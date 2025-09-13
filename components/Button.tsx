import { StyleSheet, View, Pressable, Text } from "react-native";

type Props = {
  label: string;
};

export default function Button({ label }: Props) {
  return (
    <View style={styles.buttonContainer}>
      <Pressable
        style={styles.button}
        onPress={() => alert("You pressed a button.")}
      >
        <Text style={styles.buttonLabel}>{label}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  buttonContainer: {
    margin: 10, // Add margin for spacing between buttons
    backgroundColor: "white",
    borderColor: "black",
    borderWidth: 1, // Add border width for visibility
    borderRadius: 10, // Rounded corners
    width: '90%',  
    height: '90%',
  },
  button: {
    borderRadius: 10,
    width: "100%",
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  buttonLabel: {
    fontSize: 16,
    color:'black'
  },
});
