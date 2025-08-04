// js/client.js
import { db } from "./firebase-config.js";
import { ref, push, onValue, remove } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-database.js";

window.addEventListener('DOMContentLoaded', () => {
  const counterEl = document.getElementById('counter');
  const resultEl  = document.getElementById('resultado');

  const participantsRef = ref(db, 'participants');
  const drawRef         = ref(db, 'draw/current');

  // Recupera do localStorage
  let partKey = localStorage.getItem('participantKey');
  let partRef = partKey ? ref(db, `participants/${partKey}`) : null;
  let lastDrawTS = localStorage.getItem('lastDrawTS');

  // Atualiza contador de participantes em tempo real
  onValue(participantsRef, snap => {
    const count = Object.keys(snap.val() || {}).length;
    counterEl.textContent = `Participantes: ${count}`;
  });

  // Função para registrar (ou re-registrar) participante
  function registerParticipant() {
    // Se já havia um registro, remove-o
    if (partKey) {
      remove(ref(db, `participants/${partKey}`));
    }
    // Cria novo
    const newRef = push(participantsRef, { joinedAt: Date.now() });
    partKey = newRef.key;
    partRef = newRef;
    localStorage.setItem('participantKey', partKey);
  }

  // Quando o admin sorteia (ou atualiza) draw/current
  onValue(drawRef, snapshot => {
    const data = snapshot.val();
    if (!data) return;
    const { number, min, max, timestamp } = data;

    // Se timestamp mudou, é novo sorteio: re-registra participante
    if (!lastDrawTS || Number(lastDrawTS) !== timestamp) {
      registerParticipant();
      lastDrawTS = timestamp;
      localStorage.setItem('lastDrawTS', timestamp);
      alert("🆕 Novo sorteio detectado! Seu registro foi atualizado.");
    }

    // Cálculo de pseudo número
    const keySeg = partKey.slice(-6);
    const raw    = parseInt(keySeg, 36);
    const range  = max - min + 1;
    const pseudo = (raw % range) + min;

    // Spinner visual
    let ticks = 0;
    const spin = setInterval(() => {
      const temp = Math.floor(Math.random() * range) + min;
      resultEl.textContent = `🎲 ${temp}`;
      resultEl.style.color = "#888";
      if (++ticks > 20) {
        clearInterval(spin);
        // Exibe resultado final
        if (pseudo === number) {
          alert(`🎉 Parabéns! Você foi sorteado com o número ${number}!`);
          document.body.style.background = "#a0e9a0";
          resultEl.textContent = `🎉 Você ganhou! Número sorteado: ${number}`;
          resultEl.style.color = "#28a745";
        } else {
          alert(`:( Você não ganhou. Número sorteado: ${number}`);
          document.body.style.background = "#f8d7da";
          resultEl.textContent = `Você não ganhou. Número sorteado: ${number}`;
          resultEl.style.color = "#dc3545";
        }
      }
    }, 80);
  });
});

