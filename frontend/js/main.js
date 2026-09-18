// Base URL for Backend API
const API_URL = "https://prefeitura-digital.onrender.com/api";
const MEDIA_URL = API_URL.replace('/api', '');

// Dark Mode Logic
function initThemeSwitches() {
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    document.querySelectorAll('.theme-switch input[type="checkbox"]:not(#is_anonima)').forEach(checkbox => {
        checkbox.checked = (currentTheme === 'dark');
    });
}

// Initialize theme on load
initThemeSwitches();

// Global theme switcher event delegation to support dynamically added switches (like in the navbar or dashboard panel)
document.addEventListener('change', (e) => {
    if (e.target.id === 'is_anonima') return;
    
    const themeCheckbox = e.target.closest('.theme-switch input[type="checkbox"]');
    if (themeCheckbox) {
        const isDark = themeCheckbox.checked;
        const newTheme = isDark ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Sync all other theme switches on the page in real-time
        document.querySelectorAll('.theme-switch input[type="checkbox"]:not(#is_anonima)').forEach(checkbox => {
            if (checkbox !== themeCheckbox) {
                checkbox.checked = isDark;
            }
        });
    }
});

// Accessibility: Font Size
let currentFontSizeOffset = 0;
function changeFontSize(step) {
    currentFontSizeOffset += step;
    if (currentFontSizeOffset > 3) currentFontSizeOffset = 3;
    if (currentFontSizeOffset < -1) currentFontSizeOffset = -1;
    
    const root = document.documentElement;
    // Base font size is 16px, we adjust by 2px steps
    const newSize = 16 + (currentFontSizeOffset * 2);
    root.style.fontSize = `${newSize}px`;
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
    window.location.href = '/login.html';
}

function resetSession() {
    localStorage.clear();
    alert("Sessão limpa com sucesso. Por favor, faça login novamente.");
    window.location.href = '/login.html';
}

const originalFetch = window.fetch;

window.fetch = async (...args) => {
    try {
        const response = await originalFetch(...args);
        const urlStr = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
        if (response.status === 401 && !urlStr.includes('/auth/login')) {
            console.warn("Unauthorized! Logging out...");
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            const path = window.location.pathname;
            const isAdminLoginPage = path.includes('admin/index.html') || path === '/admin' || path === '/admin/';
            // Redirecionar para a página de login correta conforme o contexto
            if (!path.includes('login.html') && !isAdminLoginPage) {
                if (path.includes('admin.html') || path.includes('/admin/')) {
                    window.location.href = '/admin/index.html';
                } else {
                    window.location.href = '/login.html?error=session_expired';
                }
            }
        }
        return response;
    } catch (err) {
        console.error("Erro na conexão com a API:", err.message);
        throw err;
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
        let role = user.tipo_usuario || '';
        if (typeof role === 'string' && role.includes('.')) {
            role = role.split('.').pop();
        }
        
        const isAdmin = role === 'admin' || role === 'subadmin';
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
        let role = user.tipo_usuario || '';
        if (typeof role === 'string' && role.includes('.')) {
            role = role.split('.').pop();
        }
        let dashboardLink = (role === 'admin' || role === 'subadmin') ? 'admin.html' : 'dashboard.html';
        navLinks.innerHTML = `
            <a href="index.html">Início</a>
            <a href="${dashboardLink}">Meu Painel</a>
            <span style="display: block; color: var(--text-secondary)">Olá, ${user.nome.split(' ')[0]}</span>
            <button id="pwa-install-btn" onclick="promptPWAInstall()" class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; background: #2563eb; color: #fff; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem;">
                <i class="fa-solid fa-mobile-screen-button"></i> Instalar App
            </button>
            <div class="theme-switch-wrapper" style="margin: 0 0.5rem; display: flex; align-items: center;">
                <label class="theme-switch" for="checkbox-theme-nav" style="margin: 0;">
                    <input type="checkbox" id="checkbox-theme-nav" />
                    <div class="slider round"></div>
                </label>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <button onclick="if(typeof abrirModalMinhaConta === 'function'){abrirModalMinhaConta();}else{window.location.href='dashboard.html';}" class="btn btn-outline" style="font-size: 0.8rem; padding: 0.4rem 0.8rem;"><i class="fa-solid fa-user"></i> Minha Conta</button>
                <button onclick="logout()" class="btn btn-outline" style="font-size: 0.8rem; padding: 0.4rem 0.8rem;">Sair</button>
            </div>
        `;
        // Sync dynamic switcher checked state immediately
        initThemeSwitches();
    }


    // Hamburger Menu Toggle (com delegação de eventos)
    document.addEventListener('click', (e) => {
        const hamburgerBtn = e.target.closest('.hamburger');
        if (hamburgerBtn) {
            const nav = document.querySelector('.nav-links');
            if (nav) {
                nav.classList.toggle('active');
                hamburgerBtn.classList.toggle('active');
            }
            return;
        }

        // Fechar o menu ao clicar fora dele no mobile
        const navLinks = document.querySelector('.nav-links');
        if (navLinks && navLinks.classList.contains('active') && !e.target.closest('.nav-links') && !e.target.closest('.hamburger')) {
            navLinks.classList.remove('active');
            const activeHamburger = document.querySelector('.hamburger.active');
            if (activeHamburger) activeHamburger.classList.remove('active');
        }
    });
    
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

// ==========================================
// MURAL DE AVISOS (CIDADÃO)
// ==========================================
async function fetchAvisos() {
    const container = document.getElementById('citizenAvisosContainer');
    if (!container) return; // Only runs on dashboard

    try {
        const res = await fetch(`${API_URL}/avisos`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        let html = '';
        data.forEach(a => {
            let bgColor = 'var(--bg-body)';
            let borderColor = '#3b82f6';
            let iconClass = 'fa-circle-info';
            let titleColor = '#1e3a8a';
            
            if (a.tipo === 'alerta') {
                borderColor = '#f59e0b';
                iconClass = 'fa-triangle-exclamation';
                titleColor = '#92400e';
                bgColor = '#fffbeb';
            } else if (a.tipo === 'urgente') {
                borderColor = '#ef4444';
                iconClass = 'fa-circle-exclamation';
                titleColor = '#991b1b';
                bgColor = '#fef2f2';
            }

            html += `
                <div style="background: ${bgColor}; border-left: 5px solid ${borderColor}; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); position: relative;">
                    <div style="display: flex; align-items: flex-start; gap: 1rem;">
                        <i class="fa-solid ${iconClass}" style="font-size: 1.5rem; color: ${borderColor}; margin-top: 3px;"></i>
                        <div style="flex: 1;">
                            <h4 style="color: ${titleColor}; margin-bottom: 0.5rem; font-size: 1.1rem; display: flex; justify-content: space-between; align-items: center;">
                                <span>${a.titulo}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;"><i class="fa-regular fa-clock"></i> ${new Date(a.data_criacao).toLocaleDateString()}</span>
                            </h4>
                            <p style="color: var(--text-color); font-size: 0.95rem; line-height: 1.6;">${a.mensagem.replace(/\n/g, '<br>')}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error("Erro ao carregar avisos:", e);
    }
}

// Call on load if container exists
document.addEventListener('DOMContentLoaded', () => {
    fetchAvisos();
});

// PWA Service Worker Registration & Install Prompt
// PWA Service Worker Registration & Install Prompt
let deferredPrompt;

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            })
            .catch(err => {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Garante o funcionamento do botão em qualquer momento (Android / iOS / PC)
document.addEventListener('DOMContentLoaded', () => {
    // Garante que a função promptPWAInstall esteja acessível no escopo global window
    window.promptPWAInstall = promptPWAInstall;
});

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    const pwaInstallBtn = document.getElementById('pwa-install-btn');
    if (pwaInstallBtn) {
        pwaInstallBtn.style.display = 'inline-flex';
    }
});

// Função para disparar a instalação (suporte completo a iOS e Android com estimativa)
function promptPWAInstall() {
    const user = getUserInfo();
    const token = getToken();

    // Bloqueia a instalação para usuários não cadastrados/não logados (proíbe anônimos)
    if (!user || !token) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Cadastro Necessário!',
                html: `
                    <div style="font-size: 1.05rem; line-height: 1.6; color: #334155; padding: 10px 0;">
                        Para baixar o aplicativo <b>Colônia Digital</b>, é necessário fazer login ou criar seu cadastro de cidadão primeiro.
                    </div>
                `,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: '<i class="fa-solid fa-user-plus"></i> Criar Cadastro',
                cancelButtonText: '<i class="fa-solid fa-right-to-bracket"></i> Fazer Login',
                confirmButtonColor: '#2563eb',
                cancelButtonColor: '#004D40'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = 'register.html';
                } else if (result.dismiss === Swal.DismissReason.cancel) {
                    window.location.href = 'login.html';
                }
            });
        } else {
            alert("Cadastro Necessário!\nPara baixar o aplicativo Colônia Digital, é necessário fazer login ou criar seu cadastro de cidadão primeiro.");
            window.location.href = 'register.html';
        }
        return;
    }

    const userAgent = window.navigator.userAgent.toLowerCase();
    const isIOS = /iphone|ipad|ipod/.test(userAgent);
    const isStandalone = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches;

    // Envia registro estatístico com dados do usuário cadastrado para o painel do administrador
    const deviceType = isIOS ? "ios" : (userAgent.includes("android") ? "android" : "desktop");
    let url = `${API_URL}/admin/metrics/pwa-install?dispositivo=${deviceType}`;
    if (user.nome) url += `&usuario_nome=${encodeURIComponent(user.nome)}`;
    if (user.cpf) url += `&usuario_cpf=${encodeURIComponent(user.cpf)}`;
    if (user.id) url += `&usuario_id=${user.id}`;
    
    try {
        fetch(url, { method: 'POST' }).catch(() => {});
    } catch(e) {}

    if (isStandalone) {
        Swal.fire({
            title: 'Aplicativo Já Instalado! 🎉',
            text: 'Você já está utilizando o Leopoldina Digital em modo aplicativo.',
            icon: 'success',
            confirmButtonText: 'Ótimo',
            confirmButtonColor: '#1e3a8a'
        });
        return;
    }

    if (isIOS) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Instalar Aplicativo no iPhone/iPad 📲',
                html: `
                    <div style="text-align: left; font-size: 0.95rem; line-height: 1.6; color: #334155;">
                        <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 10px 14px; border-radius: 6px; margin-bottom: 15px;">
                            <strong style="color: #1e3a8a;"><i class="fa-solid fa-bolt" style="color: #f59e0b;"></i> Instalação ultrarrápida:</strong> ~3 segundos (Sem ocupar memória).
                        </div>
                        <strong>Siga os passos abaixo:</strong>
                        <ol style="margin-top: 8px; padding-left: 20px;">
                            <li style="margin-bottom: 10px;">Toque no botão <b>Compartilhar</b> <i class="fa-solid fa-share-from-square" style="color: #2563eb; font-size: 1.1rem;"></i> (na barra inferior do Safari).</li>
                            <li style="margin-bottom: 10px;">Role para baixo na lista de opções.</li>
                            <li style="margin-bottom: 10px;">Selecione <b>"Adicionar à Tela de Início"</b> <i class="fa-solid fa-plus-square" style="color: #16a34a; font-size: 1.1rem;"></i>.</li>
                            <li>Toque em <b>Adicionar</b> no canto superior direito.</li>
                        </ol>
                    </div>
                `,
                icon: 'info',
                confirmButtonText: 'Entendi, vou adicionar',
                confirmButtonColor: '#2563eb'
            });
        } else {
            alert("Para instalar no seu iPhone/iPad (instalação em ~3 seg):\n\n1. Toque no ícone Compartilhar (barra inferior do Safari).\n2. Selecione 'Adicionar à Tela de Início'.\n3. Toque em 'Adicionar'.");
        }
        return;
    }

    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                let progress = 0;
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Baixando e Instalando... 🚀',
                        html: `
                            <div style="font-size: 0.95rem; color: #334155; margin-bottom: 12px;">Tempo estimado: <b>~3 segundos</b></div>
                            <div style="width: 100%; background: #e2e8f0; border-radius: 10px; height: 16px; overflow: hidden; position: relative;">
                                <div id="pwa-progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #2563eb, #10b981); transition: width 0.1s linear;"></div>
                            </div>
                            <div id="pwa-progress-text" style="font-weight: 700; font-size: 1.1rem; color: #2563eb; margin-top: 10px;">0%</div>
                        `,
                        showConfirmButton: false,
                        allowOutsideClick: false
                    });

                    const interval = setInterval(() => {
                        progress += 10;
                        const bar = document.getElementById('pwa-progress-bar');
                        const text = document.getElementById('pwa-progress-text');
                        if (bar) bar.style.width = progress + '%';
                        if (text) text.innerText = progress + '%';

                        if (progress >= 100) {
                            clearInterval(interval);
                            setTimeout(() => {
                                Swal.fire({
                                    title: '100% Instalado! 🎉',
                                    text: 'O aplicativo Leopoldina Digital já está disponível na sua tela inicial.',
                                    icon: 'success',
                                    confirmButtonText: 'Abrir App',
                                    confirmButtonColor: '#16a34a'
                                });
                            }, 400);
                        }
                    }, 250);
                }
            }
            deferredPrompt = null;
        });
    } else {
        // Fallback genérico (Chrome Android ou outros navegadores)
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Instalar Aplicativo 📲',
                html: `
                    <div style="text-align: left; font-size: 0.95rem; line-height: 1.6; color: #334155;">
                        <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 10px 14px; border-radius: 6px; margin-bottom: 15px;">
                            <strong style="color: #1e3a8a;"><i class="fa-solid fa-bolt" style="color: #f59e0b;"></i> Instalação ultrarrápida:</strong> ~3 segundos.
                        </div>
                        <strong>Como instalar:</strong>
                        <ol style="margin-top: 8px; padding-left: 20px;">
                            <li style="margin-bottom: 10px;">Clique nos <b>3 pontinhos</b> <i class="fa-solid fa-ellipsis-vertical"></i> no canto superior do navegador.</li>
                            <li>Selecione <b>"Instalar aplicativo"</b> ou <b>"Adicionar à Tela inicial"</b>.</li>
                        </ol>
                    </div>
                `,
                icon: 'info',
                confirmButtonText: 'Entendi',
                confirmButtonColor: '#2563eb'
            });
        }
    }
}

// Evento nativo quando o app termina de ser instalado no sistema do celular/PC
window.addEventListener('appinstalled', () => {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: '100% Instalado com Sucesso! 🎉',
            text: 'O ícone do Leopoldina Digital já foi adicionado à sua Tela Inicial.',
            icon: 'success',
            confirmButtonText: 'Excelente!',
            confirmButtonColor: '#16a34a'
        });
    }
});

