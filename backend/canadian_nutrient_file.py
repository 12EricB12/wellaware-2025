import pandas as pd
import os
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

# Base path for CNF CSV files
CNF_BASE_PATH = "./backend/cnf-fcen-csv"

# Load CNF data once when module is imported
try:
    # Try different encodings to handle French characters
    encodings_to_try = ['latin1', 'cp1252', 'iso-8859-1', 'utf-8']
    
    for encoding in encodings_to_try:
        try:
            food_name_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "FOOD NAME.csv"), encoding=encoding)
            nutrient_amount_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "NUTRIENT AMOUNT.csv"), encoding=encoding)
            nutrient_name_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "NUTRIENT NAME.csv"), encoding=encoding)
            measure_name_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "MEASURE NAME.csv"), encoding=encoding)
            conversion_factor_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "CONVERSION FACTOR.csv"), encoding=encoding)
            food_source_df = pd.read_csv(os.path.join(CNF_BASE_PATH, "FOOD SOURCE.csv"), encoding=encoding)
            print(f"CNF database loaded successfully using {encoding} encoding")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise Exception("Could not load files with any of the attempted encodings")
        
except Exception as e:
    print(f"Warning: Unable to load CNF files: {e}")
    food_name_df = nutrient_amount_df = nutrient_name_df = measure_name_df = conversion_factor_df = food_source_df = None

def get_nutrition_facts_and_serving_size(food_id: int) -> Dict:
    """
    Get nutrition facts and serving size information for a given food ID.
    
    Args:
        food_id (int): The FoodID to look up
        
    Returns:
        Dict: Contains food information, nutrition facts, and available serving sizes
    """
    if any(df is None for df in [food_name_df, nutrient_amount_df, nutrient_name_df, measure_name_df, conversion_factor_df, food_source_df]):
        return {"error": "CNF database not loaded properly"}
    
    # Get food information
    food_info = food_name_df[food_name_df['FoodID'] == food_id]
    if food_info.empty:
        return {"error": f"Food ID {food_id} not found"}
    
    food_data = food_info.iloc[0]
    
    # Get nutrition facts
    nutrients = nutrient_amount_df[nutrient_amount_df['FoodID'] == food_id]
    
    # Merge with nutrient names to get readable names
    nutrition_facts = nutrients.merge(
        nutrient_name_df[['NutrientID', 'NutrientName', 'NutrientUnit', 'NutrientSymbol']], 
        on='NutrientID', 
        how='left'
    )
    
    # Get serving sizes (conversion factors and measure names)
    serving_sizes = conversion_factor_df[conversion_factor_df['FoodID'] == food_id]
    serving_sizes = serving_sizes.merge(
        measure_name_df[['MeasureID', 'MeasureDescription']], 
        on='MeasureID', 
        how='left'
    )
    
    
    # Format nutrition facts
    nutrition_dict = {}
    for _, nutrient in nutrition_facts.iterrows():
        nutrition_dict[nutrient['NutrientSymbol']] = {
            'name': nutrient['NutrientName'],
            'value': nutrient['NutrientValue'],
            'unit': nutrient['NutrientUnit']
        }
    
    # Format serving sizes
    serving_sizes_list = []
    for _, serving in serving_sizes.iterrows():
        print(f"MEASURE ID: {serving['MeasureID']}")
        print(measure_name_df[measure_name_df['MeasureID'] == serving['MeasureID']])
        serving_sizes_list.append({
            'measure_id': serving['MeasureID'],
            'description': serving['MeasureDescription'],
            'conversion_factor': serving['ConversionFactorValue']
        })

    # Format food source
    food_source_list = []
    print(food_source_df[food_source_df['FoodSourceID'] == food_data['FoodSourceID']]['FoodSourceDescription'].values)
    
    return {
        'food_id': food_id,
        'food_code': food_data['FoodCode'],
        'food_name': food_data['FoodDescription'],
        'food_name_french': food_data['FoodDescriptionF'],
        'food_group_id': food_data['FoodGroupID'],
        'food_source': food_data['FoodSourceID'],
        'nutrition_facts': nutrition_dict,
        'serving_sizes': serving_sizes_list,
        'total_nutrients': len(nutrition_facts),
        'total_serving_sizes': len(serving_sizes_list),
        'date_of_entry': food_data["FoodDateOfEntry"]
    }

def search_cnf(food_name: str, max_results: int = 5) -> Dict:
    """
    Search Canadian Nutrient File for a food item by name.
    
    Args:
        food_name (str): The food name to search for
        max_results (int): Maximum number of results to return
        
    Returns:
        Dict: Search results with food IDs and names
    """
    if food_name_df is None:
        return {"error": "CNF database not loaded properly"}
    
    # Search in both English and French descriptions
    results = food_name_df[
        food_name_df['FoodDescription'].str.contains(food_name, case=False, na=False) |
        food_name_df['FoodDescriptionF'].str.contains(food_name, case=False, na=False)
    ]

    if results.empty:
        return {"results": [], "message": f"No matches found for '{food_name}'."}

    # Format results
    formatted_results = []
    for _, row in results.head(max_results).iterrows():
        formatted_results.append({
            'food_id': row['FoodID'],
            'food_code': row['FoodCode'],
            'food_name': row['FoodDescription'],
            'food_name_french': row['FoodDescriptionF'],
            'food_group_id': row['FoodGroupID']
        })
    
    return {
        "results": formatted_results,
        "total_found": len(results),
        "showing": len(formatted_results)
    }

def get_nutrition_for_multiple_foods(food_ids: List[int]) -> Dict:
    """
    Get nutrition facts and serving sizes for multiple food IDs.
    
    Args:
        food_ids (List[int]): List of FoodIDs to look up
        
    Returns:
        Dict: Contains results for each food ID
    """
    results = {}
    for food_id in food_ids:
        results[food_id] = get_nutrition_facts_and_serving_size(food_id)
    
    return results

def format_results(food_id, results):
    # Format nutrition facts
    query_result = results[food_id]
    nutrition_facts = {}

    # Get first non-zero serving
    servingSize = None
    for serving in query_result["serving_sizes"]:
        # if we don't have any serving size information, keep going
        if serving['description'] == float('nan') or serving['description'] == None:
            continue
        if re.search(r"[\d.]+", str(serving['description'])) is None:
            continue
        if serving['conversion_factor'] > 0 and float(re.search(r"[\d.]+", str(serving['description'])).group()) > 0:
            servingSize = serving
            break

    # servingSize = None if len(query_result["serving_sizes"]) == 0 else query_result["serving_sizes"][0]
    convRate = 1 if servingSize is None else servingSize['conversion_factor']
    for nutrient in list(query_result["nutrition_facts"].values()):
        nutrition_facts[nutrient["name"]] = f'{float(nutrient["value"]) * convRate} {nutrient["unit"]}'
    
    final_data = {
        "productName": query_result["food_name"],
        "source": "cnf", 
        'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
        "details": {
            "foodCode": int(query_result["food_code"]),
            "nutritionFacts": {
                "servingSize": None if servingSize is None else f'{float(servingSize['conversion_factor'])*100}{"".join(re.findall(r"[^\d.]+", str(servingSize['description'])))}', 
                "nutrition": nutrition_facts
                }
            },
            "lastUpdated": query_result["date_of_entry"],
            "productNameFrench": query_result["food_name_french"]
        }
    
    final_data = {k: v for k, v in final_data.items() if v != None and v != float('nan')}
    return final_data

def save_results(results, path):
    if not os.path.exists(f'./{path}'):
        os.makedirs(f'./{path}')

    with open(f'./{path}/cnf.jsonl', 'a') as f:
        json.dump(results, f)
        f.write('\n')

ids = list(food_name_df["FoodID"])
for id in ids:
    results = format_results(id, get_nutrition_for_multiple_foods([id]))
    save_results(results, './backend/cnf')
