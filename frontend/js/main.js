// Base URL for Backend API
const API_URL = "https://prefeitura-digital.onrender.com/api";
const MEDIA_URL = API_URL.replace('/api', '');

// Dark Mode Logic
const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
const currentTheme = localStorage.getItem('theme');

if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
    if (toggleSwitch && currentTheme === 'dark') {
        toggleSwitch.checked = true;
    }
}

function switchTheme(e) {
    if (e.target.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }    
}

if (toggleSwitch) {
    toggleSwitch.addEventListener('change', switchTheme, false);
}

// Global Auth Management
function getToken() {
    return localStorage.getItem('access_token');
}

function getUserInfo() {
    const userStr = localStorage.getItem('user_info');
    return userStr ? JSON.parse(userStr) : null;
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    window.location.href = 'login.html';
}

function checkAuth(requireAdmin = false) {
    const token = getToken();
    const user = getUserInfo();
    
    if (!token || !user) {
        window.location.href = 'login.html';
        return false;
    }
    
    if (requireAdmin && user.tipo_usuario !== 'admin') {
        window.location.href = 'dashboard.html';
        return false;
    }
    return true;
}

// Update Navbar based on Auth state
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.getElementById('nav-links');
    if (!navLinks) return;
    
    const user = getUserInfo();
    if (user) {
        let dashboardLink = user.tipo_usuario === 'admin' ? 'admin.html' : 'dashboard.html';
        navLinks.innerHTML = `
            <a href="index.html">Início</a>
            <a href="${dashboardLink}">Meu Painel</a>
            <span style="display: block; color: var(--text-secondary)">Olá, ${user.nome.split(' ')[0]}</span>
            <button onclick="logout()" class="btn btn-outline">Sair</button>
        `;
    }

    // Hamburger Menu Toggle
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            const nav = document.querySelector('.nav-links');
            nav.classList.toggle('active');
        });
    }
});

// AI Chat Integration
function toggleChat() {
    const window = document.getElementById('chat-window');
    window.classList.toggle('active');
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    // Add user msg to UI
    appendChatMsg(msg, 'user');
    input.value = '';

    try {
        const token = getToken() || "";
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_URL}/chat-ia/`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ mensagem: msg })
        });
        
        if (response.ok) {
            const data = await response.json();
            appendChatMsg(data.resposta, 'ia');
        } else {
            appendChatMsg('Erro ao conectar com a IA.', 'ia');
        }
    } catch (err) {
        appendChatMsg('Erro de rede.', 'ia');
    }
}

function appendChatMsg(text, sender) {
    const body = document.getElementById('chatBody');
    if(!body) return;
    const div = document.createElement('div');
    div.className = `chat-msg msg-${sender}`;
    div.innerText = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}
// Unified Hero Background Animation for all pages
function initBackgroundAnimation(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const totalFrames = 80;
    let currentFrame = 0;
    const fps = 12;
    const frameInterval = 1000 / fps;

    // Use absolute path relative to domain to ensure consistency across multiple subpaths if needed
    const basePath = "imagens/";

    for (let i = 0; i < totalFrames; i++) {
        const imgNum = i.toString().padStart(3, '0');
        const img = document.createElement('img');
        img.src = `${basePath}Geração_de_Vídeo_Animado_de_Hologramas_${imgNum}.jpg`;
        
        // CSS expects either .active on .hero-img (homepage) or .bg-animation-img (login)
        // We will make it flexible by applying both classes to be sure
        img.className = 'hero-img bg-animation-img';
        img.style.transition = 'none'; // Instant swap like a video

        if (i === 0) img.classList.add('active');
        container.appendChild(img);
    }

    const frames = container.querySelectorAll('img');
    if (frames.length > 1) {
        setInterval(() => {
            frames[currentFrame].classList.remove('active');
            currentFrame = (currentFrame + 1) % totalFrames;
            frames[currentFrame].classList.add('active');
        }, frameInterval);
    }
}
