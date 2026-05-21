// Base URL for Backend API
const API_URL = "https://prefeitura-digital.onrender.com/api";
const MEDIA_URL = API_URL.replace('/api', '');

// Dark Mode Logic
function initThemeSwitches() {
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    document.querySelectorAll('.theme-switch input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = (currentTheme === 'dark');
    });
}

// Initialize theme on load
initThemeSwitches();

// Global theme switcher event delegation to support dynamically added switches (like in the navbar or dashboard panel)
document.addEventListener('change', (e) => {
    const themeCheckbox = e.target.closest('.theme-switch input[type="checkbox"]');
    if (themeCheckbox) {
        const isDark = themeCheckbox.checked;
        const newTheme = isDark ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Sync all other theme switches on the page in real-time
        document.querySelectorAll('.theme-switch input[type="checkbox"]').forEach(checkbox => {
            if (checkbox !== themeCheckbox) {
                checkbox.checked = isDark;
            }
        });
    }
});

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
    window.location.href = '/login.html';
}

function resetSession() {
    localStorage.clear();
    alert("Sessão limpa com sucesso. Por favor, faça login novamente.");
    window.location.href = '/login.html';
}

// Global Fetch Wrapper with Retry Logic for Cold Starts (Render free tier)
const originalFetch = window.fetch;
let _coldStartToast = null;

function showColdStartToast() {
    if (_coldStartToast) return;
    _coldStartToast = document.createElement('div');
    _coldStartToast.id = 'coldStartToast';
    _coldStartToast.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Conectando ao servidor... Aguarde alguns segundos.';
    _coldStartToast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#1e293b;color:#fff;padding:12px 24px;border-radius:12px;font-size:0.9rem;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,0.3);display:flex;align-items:center;gap:10px;animation:fadeIn 0.3s ease;';
    document.body.appendChild(_coldStartToast);
}

function hideColdStartToast() {
    if (_coldStartToast) {
        _coldStartToast.remove();
        _coldStartToast = null;
    }
}

window.fetch = async (...args) => {
    let attempts = 0;
    const maxAttempts = 5;
    const baseDelay = 3000; // 3 seconds base delay for Render cold starts

    while (attempts < maxAttempts) {
        try {
            const response = await originalFetch(...args);
            hideColdStartToast();
            if (response.status === 401) {
                console.warn("Unauthorized! Logging out...");
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                const path = window.location.pathname;
                // Redirecionar para a página de login correta conforme o contexto
                if (!path.includes('login.html') && !path.includes('admin/index.html')) {
                    if (path.includes('admin.html') || path.includes('/admin/')) {
                        window.location.href = '/admin/index.html';
                    } else {
                        window.location.href = '/login.html?error=session_expired';
                    }
                }
            }
            return response;
        } catch (err) {
            attempts++;
            console.warn(`Tentativa de conexão ${attempts}/${maxAttempts} falhou:`, err.message);
            if (attempts >= maxAttempts) {
                hideColdStartToast();
                throw err;
            }
            // Show loading toast after first failure (cold start likely)
            if (attempts === 1) showColdStartToast();
            await new Promise(resolve => setTimeout(resolve, baseDelay * attempts));
        }
    }
};

function checkAuth(requireAdmin = false) {
    const token = getToken();
    const user = getUserInfo();
    
    if (!token || !user) {
        // Não redirecionar aqui — deixar o chamador decidir o destino correto
        return false;
    }
    
    if (requireAdmin) {
        const isAdmin = user.tipo_usuario === 'admin' || user.tipo_usuario === 'subadmin';
        if (!isAdmin) {
            // Usuário logado mas não é admin — enviar para dashboard cidadão
            window.location.href = 'dashboard.html';
            return false;
        }
    }
    return true;
}

// Update Navbar based on Auth state
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.getElementById('nav-links');
    if (!navLinks) return;
    
    const user = getUserInfo();
    if (user) {
        let dashboardLink = (user.tipo_usuario === 'admin' || user.tipo_usuario === 'subadmin') ? 'admin.html' : 'dashboard.html';
        navLinks.innerHTML = `
            <a href="index.html">Início</a>
            <a href="${dashboardLink}">Meu Painel</a>
            <span style="display: block; color: var(--text-secondary)">Olá, ${user.nome.split(' ')[0]}</span>
            <div class="theme-switch-wrapper" style="margin: 0 0.5rem; display: flex; align-items: center;">
                <label class="theme-switch" for="checkbox-theme-nav" style="margin: 0;">
                    <input type="checkbox" id="checkbox-theme-nav" />
                    <div class="slider round"></div>
                </label>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <button onclick="abrirModalTrocaSenha()" class="btn btn-outline" style="font-size: 0.8rem; padding: 0.4rem 0.8rem;"><i class="fa-solid fa-key"></i></button>
                <button onclick="logout()" class="btn btn-outline" style="font-size: 0.8rem; padding: 0.4rem 0.8rem;">Sair</button>
            </div>
        `;
        // Sync dynamic switcher checked state immediately
        initThemeSwitches();
    }


    // Hamburger Menu Toggle
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            const nav = document.querySelector('.nav-links');
            nav.classList.toggle('active');
        });
    }
    
    // Always sync all theme switches on the page once fully loaded
    initThemeSwitches();
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

        const response = await fetch(`${API_URL}/chat-ia`, {
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
    return; // Desativado para usar a imagem de fundo estática
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
