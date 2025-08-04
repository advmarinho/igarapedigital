// js/admin.js
import { db } from "./firebase-config.js";
import { ref, onValue, set, push } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-database.js";

const participantsRef = ref(db, 'participants');
const drawRef         = ref(db, 'draw/current');
const historyRef      = ref(db, 'draw/history');

// Contador de participantes
onValue(participantsRef, snap => {
  const count = Object.keys(snap.val() || {}).length;
  document.getElementById('counter').textContent = `Participantes: ${count}`;
});

// Sorteia e salva
document.getElementById('sortear').addEventListener('click', () => {
  const min = +document.getElementById('min').value;
  const max = +document.getElementById('max').value;
  if (isNaN(min)||isNaN(max)||min>=max) { alert("Intervalo inválido."); return; }
  const number = Math.floor(Math.random()*(max-min+1))+min;
  const s = { number, min, max, timestamp: Date.now(), token: "SEGREDO_ADMIN" };
  set(drawRef, s);
  push(historyRef, s);
  document.getElementById('numero-sorteado').textContent = `Último número sorteado: ${number}`;
});

// Histórico só de ganhadores (números repetidos)
onValue(historyRef, snap => {
  const arr = Object.values(snap.val() || {}).sort((a,b)=>b.timestamp-a.timestamp).slice(0,30);
  const cnt = {};
  arr.forEach(i=>cnt[i.number]=(cnt[i.number]||0)+1);

  const ul = document.getElementById('historico-match');
  ul.innerHTML = '';
  arr.forEach(item => {
    if (cnt[item.number] > 1) {
      const li = document.createElement('li');
      li.textContent = `#${item.number} (de ${item.min} a ${item.max}) em ${new Date(item.timestamp).toLocaleString('pt-BR')}`;
      ul.appendChild(li);
    }
  });
});

// Exibe último número ao carregar
onValue(drawRef, snap => {
  const d = snap.val();
  if (d?.number) document.getElementById('numero-sorteado').textContent = `Último número sorteado: ${d.number}`;
});

