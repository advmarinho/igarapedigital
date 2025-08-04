// js/firebase-config.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js";
import { getDatabase, connectDatabaseEmulator } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyAYuPvTzXWsr85ggPwyjQSlH-P-CY328Jw",
  authDomain: "sorteador-igarape-digital.firebaseapp.com",
  databaseURL: "https://sorteador-igarape-digital-default-rtdb.firebaseio.com",
  projectId: "sorteador-igarape-digital",
  storageBucket: "sorteador-igarape-digital.appspot.com",
  messagingSenderId: "212600875536",
  appId: "1:212600875536:web:c8c6dc9345c724e5917895"
};

const app = initializeApp(firebaseConfig);
const db  = getDatabase(app);

// Sempre chame antes de qualquer push()/onValue()
connectDatabaseEmulator(db, location.hostname, 9000);
console.log("🟢 Conectado ao Emulator em:", location.hostname, "porta 9000");

export { db };

