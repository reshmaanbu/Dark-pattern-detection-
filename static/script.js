// script.js - Dark Pattern Detector frontend logic

// ── Nav toggle for mobile ──────────────────────────
function toggleNav() {
  document.getElementById('navLinks').classList.toggle('open');
}

// ── Analyze pasted text ───────────────────────────
async function analyzeText() {
  const text = document.getElementById('pasteText').value.trim();
  const resultEl = document.getElementById('textResult');
  if (!text) {
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<span style="color:#ff4444">Please paste some text first.</span>';
    return;
  }
  resultEl.style.display = 'block';
  resultEl.innerHTML = 'Analyzing...';

  try {
    const resp = await fetch('/analyze_text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await resp.json();
    if (data.error) {
      resultEl.innerHTML = `<span style="color:#ff4444">${data.error}</span>`;
      return;
    }
    const riskColor = data.score > 70 ? '#22c55e' : data.score >= 40 ? '#f59e0b' : '#ef4444';
    resultEl.innerHTML = `
      <div style="margin-bottom:.5rem">
        <strong>Honesty Score:</strong>
        <span style="color:${riskColor};font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700">${data.score}/100</span>
        <span class="risk-badge" style="background:${riskColor}22;color:${riskColor};border:1px solid ${riskColor};padding:.2rem .6rem;border-radius:100px;font-size:.8rem;margin-left:.5rem">${data.risk} Risk</span>
      </div>
      <div><strong>Flags:</strong> ${data.total_flags} suspicious sentence(s)</div>
      ${data.total_flags > 0 ? Object.entries(data.pattern_info).filter(([,v])=>v.count>0).map(([,v])=>`<div style="color:${v.color};font-size:.85rem">• ${v.label}: ${v.count}</div>`).join('') : '<div style="color:#22c55e">No dark patterns detected!</div>'}
    `;
  } catch (e) {
    resultEl.innerHTML = '<span style="color:#ff4444">Error contacting server.</span>';
  }
}

// ── Analyze screenshot via OCR ────────────────────
async function analyzeScreenshot() {
  const file = document.getElementById('screenshot').files[0];
  const resultEl = document.getElementById('screenshotResult');
  if (!file) {
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<span style="color:#ff4444">Please select an image first.</span>';
    return;
  }
  resultEl.style.display = 'block';
  resultEl.innerHTML = 'Extracting text from image...';

  const formData = new FormData();
  formData.append('image', file);

  try {
    const resp = await fetch('/screenshot', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) {
      resultEl.innerHTML = `<span style="color:#ff8800">${data.error}</span>`;
      return;
    }
    const riskColor = data.score > 70 ? '#22c55e' : data.score >= 40 ? '#f59e0b' : '#ef4444';
    resultEl.innerHTML = `
      <strong>OCR Result:</strong><br>
      Score: <span style="color:${riskColor};font-weight:700">${data.score}/100</span> — ${data.risk} Risk<br>
      Flags: ${data.total_flags}
    `;
  } catch (e) {
    resultEl.innerHTML = '<span style="color:#ff4444">Error contacting server.</span>';
  }
}

// ── Feedback ──────────────────────────────────────
async function sendFeedback(vote, url) {
  try {
    await fetch('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vote, url })
    });
    document.getElementById('feedbackMsg').style.display = 'block';
    document.querySelectorAll('.feedback-btn').forEach(b => b.disabled = true);
  } catch (e) {
    console.error('Feedback error', e);
  }
}

// ── History filter ────────────────────────────────
function filterHistory() {
  const q = document.getElementById('histSearch').value.toLowerCase();
  document.querySelectorAll('#histTable tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
