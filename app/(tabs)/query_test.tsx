import React from "react";
import {
  Text,
  Button,
  StyleSheet,
  TextInput,
  View,
  FlatList,
  ScrollView,
} from "react-native";

function ItemCard({ query }: { query: any }) {
  if (query != undefined) {
    const [currentIndex, setCurrentIndex] = React.useState(0);
    const foods = query["response"]["sources"]["usda"]["data"];

    return (
      <ScrollView style={{ backgroundColor: "#aaaaaa" }}>
        <Text style={{ fontWeight: "bold", fontSize: 24 }}>
          {foods[currentIndex]["description"]}
        </Text>
        <Text style={{ fontStyle: "italic", fontSize: 20 }}>
          Brand and manufacturer:{" "}
          {foods[currentIndex]["brandName"] != undefined
            ? foods[currentIndex]["brandName"]
            : "null"}
          ,{" "}
          {foods[currentIndex]["brandOwner"] != undefined
            ? foods[currentIndex]["brandOwner"]
            : "null"}
        </Text>
        <FlatList
          data={foods[currentIndex]["foodNutrients"]}
          keyExtractor={(item, index) => index.toString()}
          renderItem={({ item }) => (
            <Text>
              {item["nutrientName"]},{" "}
              {item["percentDailyValue"] != undefined
                ? `${item["percentDailyValue"]}%`
                : `${item["value"]}${item["unitName"]}`}
            </Text>
          )}
        />
        <Button
          title="Forwards"
          onPress={() => {
            currentIndex + 1 < foods["length"]
              ? setCurrentIndex(currentIndex + 1)
              : setCurrentIndex(currentIndex);
          }}
        />
        <Button
          title="Backwards"
          onPress={() => {
            currentIndex - 1 >= 0
              ? setCurrentIndex(currentIndex - 1)
              : currentIndex;
          }}
        />
      </ScrollView>
    );
  }
}

export default function Query() {
  const [query, onChangeQuery] = React.useState(
    "Replace this text with the food you want..."
  );
  const [ip, onChangeIp] = React.useState(
    "Replace this with the IPv4 of the machine you are running the backend from (only required if from mobile)"
  );
  const [renderCards, changeRenderCards] = React.useState(false);
  const [response, setResponse] = React.useState();

  const fetchFood = async () => {
    try {
      const response = await fetch(
        ip.length > 13
          ? `http://localhost:3000/api/food/search?q=${query}&sources=usda`
          : `http://${ip}:3000/api/food/search?q=${query}&sources=usda`
      );
      const data = await response.json();
      changeRenderCards(true);
      setResponse(data);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  return (
    <ScrollView>
      {renderCards ? (
        <ItemCard query={{ response }} />
      ) : (
        <View>
          <TextInput
            style={styles.input}
            onChangeText={onChangeQuery}
            value={query}
          />
          <TextInput
            style={styles.input}
            onChangeText={onChangeIp}
            value={ip}
          />
          <Button
            title="Send GET Request to USDA Database"
            onPress={fetchFood}
          />
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  input: {
    height: 40,
    margin: 12,
    borderWidth: 1,
    padding: 10,
  },
});
