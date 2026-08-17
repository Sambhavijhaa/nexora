import { useEffect, useState } from "react";
import api from "./api";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    api
      .get("/health")
      .then((response) => {
        setMessage(response.data.message);
      })
      .catch((error) => {
        console.error("API Error:", error);
      });
  }, []);

  return (
    <main>
      <h1>Nexora</h1>
      <p>{message}</p>
    </main>
  );
}

export default App;