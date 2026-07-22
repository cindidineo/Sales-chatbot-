// Frontend for Ava — connects to POST /chat

const chatEl = document.getElementById('chat');
const form = document.getElementById('chat-form');
const messageInput = document.getElementById('message');
const nameInput = document.getElementById('contact-name');
const emailInput = document.getElementById('contact-email');
const phoneInput = document.getElementById('contact-phone');

let history = []; // list of {role: 'user'|'assistant', content: '...'}

function appendMessage(text, role='ava'){
  const wrapper = document.createElement('div');
  wrapper.className = 'message ' + (role === 'user' ? 'user' : 'ava');
  const bubble = document.createElement('div');
  bubble.className = 'bubble ' + (role === 'user' ? 'user' : 'ava');
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  chatEl.appendChild(wrapper);
  chatEl.scrollTop = chatEl.scrollHeight;
}

form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const text = messageInput.value.trim();
  if(!text) return;

  appendMessage(text, 'user');
  history.push({role:'user', content:text});
  messageInput.value = '';

  // show typing indicator
  appendMessage('Ava is typing...', 'ava');
  const typingEl = chatEl.lastChild;

  const payload = {
    message: text,
    history: history.map(h => ({role: h.role, content: h.content})),
    contact: {
      name: nameInput.value || undefined,
      email: emailInput.value || undefined,
      phone: phoneInput.value || undefined,
    }
  };

  try{
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if(!res.ok){
      throw new Error('Server error: ' + res.status);
    }

    const data = await res.json();
    // remove typing indicator
    typingEl.remove();

    const reply = data.reply || 'Sorry, something went wrong.';
    appendMessage(reply, 'ava');
    history.push({role:'assistant', content: reply});

    if(data.handed_off){
      appendMessage('✅ Your request was forwarded to sales.', 'ava');
    }

  }catch(err){
    console.error(err);
    // remove typing indicator if present
    if(typingEl && typingEl.parentNode) typingEl.remove();
    appendMessage('Sorry, I could not reach the server. Try running the backend (FastAPI) and ensure OPENAI_API_KEY is set.', 'ava');
  }
});

// welcome
appendMessage('Hi — I\'m Ava. How can I help you today? Ask about Neurofive App, Store, or Cloud.', 'ava');
