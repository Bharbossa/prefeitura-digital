// admin-v2.js - Administrative Dashboard Logic v2.0
const ADMIN_API = `${API_URL}/admin`;

let currentRole = "";
let currentSecId = null;
let statusChart = null;
let adminMap, adminMarker;
let currentLoadedOcorrencias = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAuth(true)) {
        // Sem autenticação ou permissão de admin — redirecionar para login do painel
        window.location.href = '/admin/index.html';
        return;
    }
    
    initAdmin();

    // Mobile menu toggle logic
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) sidebar.classList.toggle('active');
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        const isClickInsideSidebar = sidebar.contains(e.target);
        const isClickOnToggle = mobileMenuBtn && mobileMenuBtn.contains(e.target);
        if (!isClickInsideSidebar && !isClickOnToggle && window.innerWidth <= 768) {
            sidebar.classList.remove('active');
        }
    });
});

async function initAdmin() {
    let user = getUserInfo();
    currentRole = user ? user.tipo_usuario : "";
    if (typeof currentRole === 'string' && currentRole.includes('.')) {
        currentRole = currentRole.split('.').pop();
    }
    currentSecId = user ? user.secretaria_id : null;

    // Safety net: if subadmin is missing secretaria_nome, fetch profile to refresh cache
    if (user && currentRole === 'subadmin' && !user.secretaria_nome) {
        try {
            const res = await fetch(`${API_URL}/auth/me`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (res.ok) {
                const refreshedUser = await res.json();
                localStorage.setItem('user_info', JSON.stringify(refreshedUser));
                user = refreshedUser;
                currentSecId = user.secretaria_id;
            }
        } catch(e) {
            console.error("Error refreshing user info:", e);
        }
    }
    
    // Update User Info in header
    document.getElementById('userName').innerText = user ? (user.nome || user.email) : '';
    document.getElementById('userRole').innerText = currentRole === 'admin' ? 'Administrador Geral' : `Sub-Administrador (${(user && user.secretaria_nome) || 'Secretaria'})`;
    document.getElementById('roleDebug').innerText = `[${currentRole}]`;
    
    // Avatar Logic
    const avatar = document.getElementById('userAvatar');
    if (user.foto_perfil) {
        const src = user.foto_perfil.startsWith('data:') ? user.foto_perfil : `${MEDIA_URL}${user.foto_perfil}`;
        avatar.innerHTML = `<img src="${src}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
    } else {
        avatar.innerText = (user.nome || user.email).charAt(0).toUpperCase();
        avatar.innerHTML = avatar.innerText; // Ensure clear previous images
    }


    setupSidebar();
    
    // Quick Actions for Admin
    const quickActions = document.getElementById('adminQuickActions');
    if (quickActions) {
        if (currentRole === 'admin') {
            quickActions.innerHTML = `<button class="btn btn-primary" onclick="showSection('admins', document.querySelectorAll('.nav-item')[4])"><i class="fa-solid fa-plus"></i> Novo Sub-Admin</button>`;
        } else {
            quickActions.innerHTML = '';
        }
    }

    loadDashboard();
    
    // Global listeners
    document.getElementById('formAdmin')?.addEventListener('submit', createSubAdmin);
}

function setupSidebar() {
    const nav = document.getElementById('sideNav');
    let html = `
        <div class="nav-item active" onclick="showSection('dashboard', this)">
            <i class="fa-solid fa-chart-line"></i><span>Dashboard</span>
        </div>
        <div class="nav-item" onclick="showSection('ocorrencias', this)">
            <i class="fa-solid fa-clipboard-list"></i><span>Ocorrências</span>
        </div>
        <div class="nav-item" onclick="showSection('agendamentos', this)">
            <i class="fa-solid fa-calendar-check"></i><span>Agendamentos</span>
        </div>
    `;

    if (currentRole === 'admin') {
        html += `
            <div class="nav-item" onclick="showSection('concursos', this)">
                <i class="fa-solid fa-trophy"></i><span>Concursos</span>
            </div>
            <div class="nav-item" onclick="showSection('usuarios', this)">
                <i class="fa-solid fa-users"></i><span>Gestão de Cidadãos</span>
            </div>
            <div class="nav-item" onclick="showSection('auditoria', this)">
                <i class="fa-solid fa-fingerprint"></i><span>Auditoria Global</span>
            </div>
            <div class="nav-item" onclick="showSection('usuarios-todos', this)">
                <i class="fa-solid fa-users-gear"></i><span>Gestão de Todos Usuários</span>
            </div>
            <div class="nav-item" onclick="showSection('contabilidade', this)">
                <i class="fa-solid fa-chart-bar"></i><span>Contabilidade</span>
            </div>
            <div class="nav-item" onclick="showSection('avisos', this)">
                <i class="fa-solid fa-bullhorn"></i><span>Mural de Avisos</span>
            </div>
            <div class="nav-item" onclick="showSection('password-resets', this)">
                <i class="fa-solid fa-key"></i><span>Senhas Solicitadas</span>
            </div>
            <div class="nav-item" onclick="showSection('alterar-senha', this)">
                <i class="fa-solid fa-lock"></i><span>Alterar Senha</span>
            </div>
        `;
    }

    const user = getUserInfo();
    const isInfra = user && user.secretaria_nome && user.secretaria_nome.toLowerCase().includes('infraestrutura');
    if (currentRole === 'admin' || (currentRole === 'subadmin' && isInfra)) {
        html += `
            <div class="nav-item" onclick="showSection('mapas', this)">
                <i class="fa-solid fa-map-location-dot"></i><span>Inteligência Geográfica</span>
            </div>
        `;
    }
    
    const allowedPanicoEmails = ['patrulhamariadapenha.gcm.clp@gmail.com', 'guardamunicipalcolonia@gmail.com'];
    const userEmail = (user && user.email) ? user.email.toLowerCase().trim() : '';
    const isPanicoSecretaria = user && (user.secretaria_id == 16 || user.secretaria_id == 17 || (user.secretaria_nome && (user.secretaria_nome.toLowerCase().includes('mulher') || user.secretaria_nome.toLowerCase().includes('guarda') || user.secretaria_nome.toLowerCase().includes('patrulha'))));
    const isPanicoAdmin = user && (allowedPanicoEmails.map(e => e.toLowerCase()).includes(userEmail) || isPanicoSecretaria);
    
    if (currentRole === 'admin' || (currentRole === 'subadmin' && isPanicoAdmin)) {
        html += `
            <div class="nav-item" onclick="showSection('gestao-panico', this)">
                <i class="fa-solid fa-triangle-exclamation"></i><span>Botão do Pânico</span>
            </div>
        `;
    }
    
    if (currentRole === 'admin' || currentRole === 'subadmin') {
        html += `
            <div class="nav-item" onclick="showSection('admins', this)">
                <i class="fa-solid fa-user-shield"></i><span>Equipe da Secretaria</span>
            </div>
        `;
    }

    html += `
        <div class="nav-item" onclick="showSection('config', this)">
            <i class="fa-solid fa-gear"></i><span>Minha Conta</span>
        </div>
    `;
    nav.innerHTML = html;
}

function showSection(sectionId, element) {
    // Role check for specific sections
    let restricted = ['usuarios', 'auditoria', 'usuarios-todos', 'contabilidade', 'mapas', 'avisos'];
    
    const user = getUserInfo();
    const isInfra = user && user.secretaria_nome && user.secretaria_nome.toLowerCase().includes('infraestrutura');
    if (currentRole === 'subadmin' && isInfra) {
        restricted = restricted.filter(r => r !== 'mapas');
    }

    if (restricted.includes(sectionId) && currentRole !== 'admin') {
        alert("Acesso restrito.");
        return;
    }

    if (sectionId === 'gestao-panico') {
        const allowedPanicoEmails = ['patrulhamariadapenha.gcm.clp@gmail.com', 'guardamunicipalcolonia@gmail.com'];
        const userEmail = (user && user.email) ? user.email.toLowerCase().trim() : '';
        const isPanicoSecretaria = user && (user.secretaria_id == 16 || user.secretaria_id == 17 || (user.secretaria_nome && (user.secretaria_nome.toLowerCase().includes('mulher') || user.secretaria_nome.toLowerCase().includes('guarda') || user.secretaria_nome.toLowerCase().includes('patrulha'))));
        const isPanicoAdmin = user && (allowedPanicoEmails.map(e => e.toLowerCase()).includes(userEmail) || isPanicoSecretaria);
        if (currentRole !== 'admin' && !isPanicoAdmin) {
            alert("Acesso restrito.");
            return;
        }
    }

    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));

    document.getElementById(sectionId).classList.add('active');
    
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    element.classList.add('active');
    
    // Breadcrumbs
    const titles = {
        'dashboard': 'Dashboard Geral',
        'ocorrencias': 'Todas Ocorrências (Global)',
        'agendamentos': 'Todos Agendamentos (Global)',
        'concursos': 'Inscrições em Concursos',
        'usuarios': 'Gestão de Cidadãos',
        'admins': 'Sub-Administradores',
        'auditoria': 'Logs de Auditoria',
        'usuarios-todos': 'Todas as Pessoas Cadastradas',
        'contabilidade': 'Contabilidade por Secretaria',
        'mapas': 'Inteligência Geográfica',
        'config': 'Minha Conta',
        'avisos': 'Mural de Avisos',
        'password-resets': 'Senhas Solicitadas',
        'gestao-panico': 'Gestão do Botão de Pânico'
    };
    document.getElementById('pageTitle').innerText = titles[sectionId];
    document.getElementById('breadcrumb').innerText = `Início / ${titles[sectionId]}`;

    // Load data specific to section
    if (sectionId === 'dashboard') loadDashboard();
    if (sectionId === 'ocorrencias') loadOcorrencias();
    if (sectionId === 'agendamentos') loadAgendamentos();
    if (sectionId === 'concursos') loadConcursos();
    if (sectionId === 'usuarios') loadUsers();
    if (sectionId === 'admins') loadAdmins();
    if (sectionId === 'auditoria') loadAuditLogs();
    if (sectionId === 'usuarios-todos') loadAllCombinedUsers();
    if (sectionId === 'contabilidade') loadPerformance();
    if (sectionId === 'mapas') {
        loadHeatmap();
        loadBairrosChart();
        loadUserHeatmap();
        // Give time for DOM to render the block to invalidate Leaflet size
        setTimeout(() => {
            if (adminHeatmap) adminHeatmap.invalidateSize();
            if (userHeatmap) userHeatmap.invalidateSize();
        }, 100);
    }
    if (sectionId === 'avisos') loadAvisosAdmin();
    if (sectionId === 'password-resets') loadPasswordResets();
    if (sectionId === 'config') { refreshConfigUI(); toggleResetCard(); }

    // Close sidebar on mobile after selection
    if (window.innerWidth <= 768) {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) sidebar.classList.remove('active');
    }
}


async function loadDashboard() {
    try {
        const res = await fetch(`${ADMIN_API}/metrics/summary`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        
        // Render Stats
        renderStats(data);
        
        // Chart
        renderDashboardChart(data.ocorrencias);
        
        // Secretariat Breakdown Chart (Admin only)
        if (currentRole === 'admin') {
            document.getElementById('secChartContainer').style.display = 'block';
            renderSecretariaChart();
        } else {
            document.getElementById('secChartContainer').style.display = 'none';
        }
        
        // Recent Activity (just reuse occurrences for now)
        loadRecentActivity();

        // Load Maps and Bairros metrics on main dashboard
        loadHeatmap();
        loadBairrosChart();
        loadUserHeatmap();
    } catch(e) { console.error(e); }
}

let secChart = null;
async function renderSecretariaChart() {
    try {
        const res = await fetch(`${ADMIN_API}/metrics/secretaria-breakdown`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        const ctx = document.getElementById('secretariaChart').getContext('2d');
        if (secChart) secChart.destroy();

        secChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.nome.split(' ').slice(-1)[0]), // Short names
                datasets: [
                    {
                        label: 'Ocorrências',
                        data: data.map(d => d.ocorrencias),
                        backgroundColor: '#2563eb'
                    },
                    {
                        label: 'Agendamentos',
                        data: data.map(d => d.agendamentos),
                        backgroundColor: '#10b981'
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } },
                scales: { y: { beginAtZero: true } }
            }
        });
    } catch(e) {}
}

let adminHeatmap = null;
async function loadHeatmap() {
    if (!adminHeatmap) {
        adminHeatmap = L.map('heatmapAdminDiv').setView([-8.9048, -35.7297], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(adminHeatmap);
    }

    try {
        const res = await fetch(`${ADMIN_API}/metrics/heatmap`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        
        // Remove camadas antigas de calor
        adminHeatmap.eachLayer((layer) => {
            if (layer._heat || layer instanceof L.Marker) adminHeatmap.removeLayer(layer);
        });

        // Adiciona dados
        const heatData = data.map(p => [p.lat, p.lng, p.weight * 2]);
        L.heatLayer(heatData, {radius: 25, blur: 15, maxZoom: 17}).addTo(adminHeatmap);
        
        if (data.length > 0) {
            const group = new L.featureGroup(data.map(p => L.marker([p.lat, p.lng])));
            adminHeatmap.fitBounds(group.getBounds(), {padding: [30, 30]});
        }
        
        setTimeout(() => adminHeatmap.invalidateSize(), 200);
    } catch (e) { console.error("Erro heatmap:", e); }
}

let userHeatmap = null;
async function loadUserHeatmap() {
    const mapDiv = document.getElementById('userHeatmapAdminDiv');
    if (!mapDiv) return;

    if (!userHeatmap) {
        userHeatmap = L.map('userHeatmapAdminDiv').setView([-8.9113702, -35.7208226], 16);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(userHeatmap);
    }

    try {
        let res = await fetch(`${ADMIN_API}/metrics/users-heatmap`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        let data = null;
        if (res.ok) {
            data = await res.json();
            
            // Garantir que cadastros do Belo Jardim/Bela Jardim/Loteamento Belo Jardim fiquem posicionados corretamente no Bairro Belo Jardim
            if (data && data.cidadaos && data.cidadaos.length > 0) {
                const newHeatPoints = [];
                data.cidadaos.forEach((c) => {
                    const addrLow = (c.endereco || '').toLowerCase();
                    const isBeloJardim = (addrLow.includes('belo') || addrLow.includes('bela')) && (addrLow.includes('jardim') || addrLow.includes('jadim') || addrLow.includes('jadin'));
                    if (isBeloJardim) {
                        const cidInt = typeof c.id === 'number' ? c.id : (parseInt(c.id) || 1);
                        const h = (cidInt * 2654435761) % 1000000;
                        const jLat = (((h % 100) - 50) / 50.0) * 0.0006;
                        const jLng = (((Math.floor(h / 100) % 100) - 50) / 50.0) * 0.0010;
                        c.lat = -8.9148500 + jLat;
                        c.lng = -35.7196500 + jLng;
                    }
                    if (c.lat && c.lng) {
                        newHeatPoints.push({ lat: c.lat, lng: c.lng, weight: 1 });
                    }
                });
                if (newHeatPoints.length > 0) {
                    data.heat_points = newHeatPoints;
                }
            }
        } else {
            const resBairro = await fetch(`${ADMIN_API}/metrics/users-bairro`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (resBairro.ok) {
                const rawBairros = await resBairro.json();
                const list = Array.isArray(rawBairros) ? rawBairros : (rawBairros.bairros || []);
                const totalSum = list.reduce((acc, item) => acc + (item.total || 0), 0);
                
                const base_coords = {
                    // Bairro Vila Nova (Rua Antônio de Barros Pereira area)
                    "Vila Nova": [-8.9145991, -35.7265750],
                    "Bairro Vila Nova": [-8.9145991, -35.7265750],
                    "Conjunto Vila Nova": [-8.9145991, -35.7265750],
                    "Loteamento Vila Nova": [-8.9145991, -35.7265750],
                    "Antônio de Barros": [-8.9145991, -35.7265750],
                    "Antonio de Barros": [-8.9145991, -35.7265750],
                    "Barros Pereira": [-8.9145991, -35.7265750],
                    "Teódulo Augusto": [-8.9118238, -35.7257887],
                    "Teodulo Augusto": [-8.9118238, -35.7257887],
                    "Teofilo Augusto": [-8.9118238, -35.7257887],
                    "Durval Gonçalves": [-8.9116432, -35.7252109],
                    "Durval Goncalves": [-8.9116432, -35.7252109],
                    "Padre Cícero": [-8.9111747, -35.7266912],
                    "Padre Cicero": [-8.9111747, -35.7266912],
                    "16 de Julho": [-8.9109060, -35.7249840],
                    "Gustavo Fitipaldi": [-8.9102588, -35.7251056],
                    "Pedro II": [-8.9107666, -35.7240646],
                    "Boa Vista": [-8.9125343, -35.7253001],

                    // Center - Town Center & Central Streets
                    "Centro": [-8.9113702, -35.7208226],
                    "Padre Francisco": [-8.9101631, -35.7196767],
                    "Severino Ferreira": [-8.9119878, -35.7183578],
                    "Genival Rodrigues": [-8.9116736, -35.7226213],
                    "Mário Lima": [-8.9121909, -35.7221742],
                    "Mario Lima": [-8.9121909, -35.7221742],
                    "7 de Setembro": [-8.9129721, -35.7229025],
                    "Setembro": [-8.9129721, -35.7229025],
                    "Manoel Ataíde": [-8.9134105, -35.7222470],
                    "Manoel Ataide": [-8.9134105, -35.7222470],
                    "Mário de Gusmão": [-8.9139014, -35.7209606],
                    "Mario de Gusmao": [-8.9139014, -35.7209606],
                    "Artur Ferreira": [-8.9091807, -35.7177514],
                    "Belo Jardim": [-8.9148500, -35.7196500],
                    "Belo Jadim": [-8.9148500, -35.7196500],
                    "Belo Jadin": [-8.9148500, -35.7196500],
                    "Bela Jardim": [-8.9148500, -35.7196500],
                    "Bela Jadim": [-8.9148500, -35.7196500],
                    "Bela Jadin": [-8.9148500, -35.7196500],
                    "Loteamento Belo Jardim": [-8.9148500, -35.7196500],
                    "Loteamento Belo Jadim": [-8.9148500, -35.7196500],
                    "Loteamento Bela Jardim": [-8.9148500, -35.7196500],
                    "Loteamento Bela Jadim": [-8.9148500, -35.7196500],
                    "Manoel Lino": [-8.9121762, -35.7243278],
                    "José Inácio": [-8.9114035, -35.7178309],
                    "Jose Inacio": [-8.9114035, -35.7178309],

                    // Right Side (East) - Bairro José Maria Quirino & East Streets
                    "José Maria Quirino": [-8.9115000, -35.7155000],
                    "Maria Quirino": [-8.9115000, -35.7155000],
                    "Quirino": [-8.9115000, -35.7155000],
                    "Filomena Freitas": [-8.9116689, -35.7156993],
                    "José Francisco Xavier": [-8.9118923, -35.7140726],
                    "José Gomes": [-8.9121455, -35.7148886],
                    "Genildo Loureiro": [-8.9118782, -35.7143524],
                    "José Maria Ramos": [-8.9106410, -35.7156470]
                };
                
                const clamp = (lt, lg) => [
                    Math.max(-8.9160, Math.min(-8.9065, lt)),
                    Math.max(-35.7270, Math.min(-35.7135, lg))
                ];
                
                const localidades = [];
                const heat_points = [];
                
                list.forEach((item, idx) => {
                    const name = item.endereco || item.bairro || item.rua || item.name || 'Desconhecido';
                    const nameLow = name.toLowerCase();
                    let lat = -8.9113702;
                    let lng = -35.7208226;
                    let found = false;
                    
                    const isBelo = (nameLow.includes('belo') || nameLow.includes('bela')) && (nameLow.includes('jardim') || nameLow.includes('jadim') || nameLow.includes('jadin'));
                    if (isBelo) {
                        lat = -8.9148500;
                        lng = -35.7196500;
                        found = true;
                    } else {
                        for (let k in base_coords) {
                            if (nameLow.includes(k.toLowerCase()) || k.toLowerCase().includes(nameLow)) {
                                lat = base_coords[k][0];
                                lng = base_coords[k][1];
                                found = true;
                                break;
                            }
                        }
                    }
                    
                    if (!found) {
                        lat = -8.9113702 + (Math.sin(idx + 1) * 0.0001);
                        lng = -35.7208226 + (Math.cos(idx + 1) * 0.0001);
                    }
                    
                    const [cLat, cLng] = clamp(lat, lng);
                    localidades.push({ name, lat: cLat, lng: cLng, total: item.total });
                    const spreadLat = isBelo ? 0.0006 : 0.0003;
                    const spreadLng = isBelo ? 0.0010 : 0.0004;
                    
                    for (let i = 0; i < item.total; i++) {
                        const [hLat, hLng] = clamp(cLat + ((Math.random() - 0.5) * 2 * spreadLat), cLng + ((Math.random() - 0.5) * 2 * spreadLng));
                        heat_points.push({ lat: hLat, lng: hLng, weight: 1 });
                    }
                });
                
                data = {
                    localidades,
                    heat_points,
                    total_cadastrados: totalSum
                };
            }
        }

        if (!data) return;

        const totalSpan = document.getElementById('totalCidadaosMapa');
        if (totalSpan) {
            totalSpan.innerText = `${data.total_cadastrados || 0} Cidadãos`;
        }

        userHeatmap.eachLayer((layer) => {
            if (layer._heat || layer instanceof L.Marker || layer instanceof L.CircleMarker || (layer.options && layer.options.gradient)) {
                userHeatmap.removeLayer(layer);
            }
        });

        if (data.heat_points && data.heat_points.length > 0) {
            const heatData = data.heat_points.map(p => [p.lat, p.lng, (p.weight || 1) * 3.5]);
            L.heatLayer(heatData, { 
                radius: 32, 
                blur: 16, 
                maxZoom: 17,
                gradient: { 0.2: '#00ff88', 0.5: '#ffff00', 0.8: '#ff5500', 1.0: '#ff0000' }
            }).addTo(userHeatmap);
        }

        const mapPoints = [];
        if (data.cidadaos && data.cidadaos.length > 0) {
            data.cidadaos.forEach(c => {
                if (!c.lat || !c.lng) return;
                
                const popupContent = `
                    <div style="padding: 6px; font-family: 'Inter', sans-serif; min-width: 220px; color: #1e293b;">
                        <div style="font-weight: 700; font-size: 0.95rem; color: #10b981; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">
                            <i class="fa-solid fa-user"></i> ${c.nome || 'Cidadão'}
                        </div>
                        <div style="font-size: 0.82rem; line-height: 1.6;">
                            <div><b>🪪 CPF:</b> ${c.cpf || 'Não informado'}</div>
                            <div><b>✉️ E-mail:</b> ${c.email || 'Não informado'}</div>
                            <div><b>📞 Telefone:</b> ${c.telefone || 'Não informado'}</div>
                            <div><b>💬 WhatsApp:</b> ${c.whatsapp || 'Não informado'}</div>
                            <div><b>📍 Endereço:</b> ${c.endereco || 'Não informado'}</div>
                            <div><b>⚧️ Gênero:</b> ${c.genero || 'Não informado'}</div>
                        </div>
                    </div>
                `;
                
                const circle = L.circleMarker([c.lat, c.lng], {
                    radius: 7,
                    fillColor: '#10b981',
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.95
                }).addTo(userHeatmap);
                
                circle.bindPopup(popupContent);
                circle.on('mouseover', function() { this.openPopup(); });
                mapPoints.push(circle);
            });
            
            if (mapPoints.length > 0) {
                const group = new L.featureGroup(mapPoints);
                userHeatmap.fitBounds(group.getBounds(), { padding: [40, 40] });
            }
        }

        setTimeout(() => {
            if (userHeatmap) userHeatmap.invalidateSize();
        }, 200);
    } catch (e) { console.error("Erro mapa de usuarios:", e); }
}

let bairrosChart = null;
let bairrosChartRawData = { bairros: [], ruas: [] };
let activeBairroMode = 'bairros';

async function loadBairrosChart() {
    try {
        const res = await fetch(`${ADMIN_API}/metrics/users-bairro`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        
        if (Array.isArray(data)) {
            bairrosChartRawData = { bairros: data, ruas: data };
        } else {
            bairrosChartRawData = data;
        }
        
        if (!bairrosChartRawData.ruas || !bairrosChartRawData.ruas.length) {
            bairrosChartRawData.ruas = bairrosChartRawData.bairros || [];
        }
        
        renderBairrosChart(activeBairroMode);
    } catch(e) { console.error("Erro grafico bairros:", e); }
}

function switchBairrosChart(mode) {
    activeBairroMode = mode;
    const btnBairro = document.getElementById('btnBairro');
    const btnRua = document.getElementById('btnRua');
    
    if (btnBairro && btnRua) {
        if (mode === 'bairros') {
            btnBairro.className = 'btn btn-sm btn-primary';
            btnRua.className = 'btn btn-sm btn-outline';
        } else {
            btnBairro.className = 'btn btn-sm btn-outline';
            btnRua.className = 'btn btn-sm btn-primary';
        }
    }
    
    renderBairrosChart(mode);
}

function renderBairrosChart(mode) {
    let list = (bairrosChartRawData && bairrosChartRawData[mode]) ? bairrosChartRawData[mode] : [];
    if (!list.length && bairrosChartRawData && bairrosChartRawData.bairros) {
        list = bairrosChartRawData.bairros;
    }
    const topData = list.slice(0, 10);

    const canvas = document.getElementById('bairrosChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (bairrosChart) bairrosChart.destroy();

    bairrosChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topData.map(d => d.endereco.length > 18 ? d.endereco.substring(0, 18) + '...' : d.endereco),
            datasets: [{
                label: mode === 'bairros' ? 'Cidadãos por Bairro' : 'Cidadãos por Rua',
                data: topData.map(d => d.total),
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => {
                            if (!items || !items.length) return '';
                            const idx = items[0].dataIndex;
                            return topData[idx]?.endereco || '';
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } },
                x: { ticks: { maxRotation: 45, minRotation: 45 } }
            }
        }
    });
}


function renderStats(data) {
    const grid = document.getElementById('statsGrid');
    
    const oc = data.ocorrencias;
    const ag = data.agendamentos;
    
    let html = `
        <div class="stat-card">
            <div class="stat-icon" style="background: #eff6ff; color: #2563eb;"><i class="fa-solid fa-clipboard-question"></i></div>
            <h4 style="color: var(--text-muted); font-size: 0.9rem;">Ocorrências Pendentes</h4>
            <h2 style="margin: 0.5rem 0;">${oc.pendentes}</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Total: ${oc.total}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background: #ecfdf5; color: #10b981;"><i class="fa-solid fa-check-to-slot"></i></div>
            <h4 style="color: var(--text-muted); font-size: 0.9rem;">Ocorrências Resolvidas</h4>
            <h2 style="margin: 0.5rem 0;">${oc.resolvidas}</h2>
            <div style="font-size: 0.8rem; color: var(--success); font-weight: 600;">Sucesso</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon" style="background: #fff7ed; color: #f59e0b;"><i class="fa-solid fa-clock-rotate-left"></i></div>
            <h4 style="color: var(--text-muted); font-size: 0.9rem;">Agendamentos Pendentes</h4>
            <h2 style="margin: 0.5rem 0;">${ag.pendentes}</h2>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Confirmados: ${ag.confirmados}</div>
        </div>
    `;

    if (currentRole === 'admin' && data.usuarios) {
        html += `
            <div class="stat-card">
                <div class="stat-icon" style="background: #fef2f2; color: #ef4444;"><i class="fa-solid fa-user-plus"></i></div>
                <h4 style="color: var(--text-muted); font-size: 0.9rem;">Cidadãos Pendentes</h4>
                <h2 style="margin: 0.5rem 0;">${data.usuarios.usuarios_pendentes}</h2>
                <div style="font-size: 0.8rem; color: var(--text-muted);">Total: ${data.usuarios.total_usuarios}</div>
            </div>
        `;
    }

    if (data.satisfacao) {
        let starColor = '#f59e0b';
        let feedback = "Ótimo";
        if (data.satisfacao.media_geral < 3) {
            starColor = '#ef4444';
            feedback = "Atenção";
        }
        
        html += `
            <div class="stat-card" style="border: 1px solid #fde68a; background: #fffdf5;">
                <div class="stat-icon" style="background: #fffbeb; color: ${starColor};"><i class="fa-solid fa-star"></i></div>
                <h4 style="color: var(--text-muted); font-size: 0.9rem;">Satisfação do Cidadão</h4>
                <h2 style="margin: 0.5rem 0; color: ${starColor}; display: flex; align-items: center; gap: 8px;">
                    ${data.satisfacao.media_geral} <span style="font-size: 1rem; color: #ccc;">/ 5.0</span>
                </h2>
                <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Status: ${feedback}</div>
            </div>
        `;
    }

    grid.innerHTML = html;
}

function renderDashboardChart(oc) {
    const ctx = document.getElementById('statusChartAdmin').getContext('2d');
    if (statusChart) statusChart.destroy();
    
    const isEmpty = oc.pendentes === 0 && oc.resolvidas === 0;

    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: isEmpty ? ['Sem Dados'] : ['Pendentes', 'Resolvidas'],
            datasets: [{
                data: isEmpty ? [1] : [oc.pendentes, oc.resolvidas],
                backgroundColor: isEmpty ? ['#e2e8f0'] : ['#f59e0b', '#10b981'],
                borderWidth: 0,
                hoverOffset: isEmpty ? 0 : 10
            }]
        },
        options: {
            cutout: '70%',
            plugins: { 
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            if (isEmpty) return ' Sem ocorrências';
                            return ' ' + context.label + ': ' + context.raw;
                        }
                    }
                }
            }
        }
    });
}

async function loadRecentActivity() {
    try {
        const headers = { 'Authorization': `Bearer ${getToken()}` };
        const [resOcorrencias, resAgendamentos] = await Promise.all([
            fetch(`${API_URL}/ocorrencias`, { headers }).catch(() => null),
            fetch(`${API_URL}/agendamentos`, { headers }).catch(() => null)
        ]);

        let items = [];

        if (resOcorrencias && resOcorrencias.ok) {
            let listOcorrencias = await resOcorrencias.json();
            if (currentSecId) listOcorrencias = listOcorrencias.filter(o => parseInt(o.secretaria_id) === parseInt(currentSecId));
            listOcorrencias.forEach(o => {
                items.push({
                    type: 'ocorrencia',
                    id: o.id,
                    titulo: o.titulo,
                    protocolo: o.protocolo || o.id,
                    dataRaw: o.data,
                    usuario_nome: o.usuario_nome,
                    status: o.status,
                    latitude: o.latitude,
                    longitude: o.longitude
                });
            });
        }

        if (resAgendamentos && resAgendamentos.ok) {
            let listAgendamentos = await resAgendamentos.json();
            const userInfo = getUserInfo();
            if (userInfo && userInfo.email === 'denilmalucass@gmail.com') {
                listAgendamentos = listAgendamentos.filter(a => a.assunto && a.assunto.toUpperCase().includes('HOSPITAL MARIA LOUREIRO'));
            } else if (userInfo && userInfo.email === 'ana.gabriela_2@hotmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('BELO JARDIM')) || (a.posto && a.posto.toUpperCase().includes('BELO JARDIM')));
            } else if (userInfo && userInfo.email === 'cassianub12@icloud.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('DANIEL MONTEIRO')) || (a.posto && a.posto.toUpperCase().includes('DANIEL MONTEIRO')));
            } else if (userInfo && userInfo.email === 'flaviadanielly381@gmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('ADAMOR')) || (a.posto && a.posto.toUpperCase().includes('ADAMOR')));
            } else if (userInfo && userInfo.email === 'vivianlmk@hotmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('LUIZ LESSA')) || (a.posto && a.posto.toUpperCase().includes('LUIZ LESSA')));
            } else if (userInfo && userInfo.email === 'ketlinandrade01@icloud.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('VILA NOVA')) || (a.posto && a.posto.toUpperCase().includes('VILA NOVA')));
            } else if (userInfo && userInfo.email === 'trajanojuliana17@gmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('TAQUARA')) || (a.posto && a.posto.toUpperCase().includes('TAQUARA')));
            } else if (userInfo && userInfo.email === 'arianacarater@gmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && a.assunto.toUpperCase().includes('ACIOLY')) || (a.posto && a.posto.toUpperCase().includes('ACIOLY')));
            } else if (userInfo && userInfo.email === 'vanuzasoares667@gmail.com') {
                listAgendamentos = listAgendamentos.filter(a => (a.assunto && (a.assunto.toUpperCase().includes('POSTO CENTRO') || a.assunto.toUpperCase().includes('PSF 02'))) || (a.posto && (a.posto.toUpperCase().includes('CENTRO') || a.posto.toUpperCase().includes('PSF 02'))));
            } else if (currentSecId) {
                listAgendamentos = listAgendamentos.filter(a => parseInt(a.secretaria_id) === parseInt(currentSecId));
            }
            listAgendamentos.forEach(a => {
                items.push({
                    type: 'agendamento',
                    id: a.id,
                    titulo: a.assunto || `Agendamento - ${a.tipo || 'Geral'}`,
                    protocolo: a.protocolo || a.id,
                    dataRaw: a.data || a.created_at,
                    usuario_nome: a.usuario_nome,
                    status: a.status
                });
            });
        }

        // Order by date descending
        items.sort((a, b) => new Date(b.dataRaw) - new Date(a.dataRaw));

        const container = document.getElementById('recentActivity');
        container.innerHTML = '';

        if (items.length === 0) {
            container.innerHTML = '<p style="text-align:center; color: var(--text-muted); padding: 3rem 0; font-size: 1.1rem;"><i class="fa-solid fa-inbox fa-2x" style="display:block; margin-bottom: 1rem; color: #cbd5e1;"></i>Nenhuma solicitação recente.</p>';
            return;
        }

        items.slice(0, 6).forEach(item => {
            const s = (item.status || '').toLowerCase();
            const statusType = (s === 'resolvido' || s === 'concluido' || s === 'atendido' || s === 'confirmado') ? 'done' : (s === 'em_atendimento' || s === 'em andamento' ? 'progress' : 'pending');
            const typeLabel = item.type === 'agendamento' ? '<span style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 6px;">Agendamento</span>' : '<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 6px;">Ocorrência</span>';

            const dateStr = item.dataRaw ? new Date(item.dataRaw).toLocaleDateString() : '';

            container.innerHTML += `
                <div style="padding: 1rem 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; font-size: 0.9rem; display: flex; align-items: center; gap: 4px;">
                            ${typeLabel} ${item.titulo}
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">#${item.protocolo} • ${dateStr}${item.usuario_nome ? ' • Cidadão: ' + item.usuario_nome : ''}</div>
                        ${item.latitude != null && item.longitude != null ? `<a href="javascript:void(0)" onclick="openAdminMap('${item.latitude}', '${item.longitude}', '${encodeURIComponent(item.titulo)}')" style="color: #10b981; font-weight: 600; text-decoration: none; font-size: 0.75rem; display: inline-block; margin-top: 2px;"><i class="fa-solid fa-location-dot"></i> Ver no Mapa</a>` : ''}
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span class="badge badge-${statusType}">${item.status}</span>
                        ${item.latitude && item.longitude ? `<button class="btn btn-outline" title="Ver no Mapa" style="border-color: #10b981; color: #10b981; padding: 4px 10px; font-size: 0.75rem;" onclick="openAdminMap('${item.latitude}', '${item.longitude}', '${encodeURIComponent(item.titulo)}')"><i class="fa-solid fa-location-dot"></i></button>` : ''}
                        ${item.type === 'ocorrencia' && currentRole==='admin' && s !== 'resolvido' ? `<button class="btn" style="background-color: #ef4444; color: white; border: none; font-weight: bold; margin-left: 8px; padding: 4px 10px; border-radius: 6px; box-shadow: 0 2px 5px rgba(239, 68, 68, 0.4); display: flex; align-items: center; gap: 5px; font-size: 0.75rem;" title="Cobrar Secretaria URGENTE" onclick="cobrarSecretaria('${item.id}')"><i class="fa-solid fa-bell fa-shake"></i> Cobrar</button>` : ''}
                    </div>
                </div>
            `;
        });
    } catch(e) { console.error(e); }
}

async function loadOcorrencias() {
    const status = document.getElementById('filterOcorrenciaStatus').value;
    const url = `${API_URL}/ocorrencias${status ? '?status='+status : ''}`;
    
    try {
        const res = await fetch(url, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            let list = await res.json();
            currentLoadedOcorrencias = list;
            
            const user = getUserInfo();
            const userSecName = (user && user.secretaria_nome ? user.secretaria_nome : '').toLowerCase();
            const userEmail = (user && user.email ? user.email : '').toLowerCase();
            const isSecMulher = currentSecId === 16 || userSecName.includes('mulher') || userSecName.includes('patrulha') || userEmail.includes('patrulhamariadapenha');

            if (currentSecId) {
                if (isSecMulher) {
                    list = list.filter(o => parseInt(o.secretaria_id) === parseInt(currentSecId) || parseInt(o.secretaria_id) === 17 || (o.titulo && (o.titulo.toLowerCase().includes('pânico') || o.titulo.toLowerCase().includes('panico'))));
                } else {
                    list = list.filter(o => parseInt(o.secretaria_id) === parseInt(currentSecId));
                }
            }
            
            const container = document.getElementById('ocorrenciasTableContainer');
            if (list.length === 0) {
                container.innerHTML = '<p style="padding: 2rem; text-align: center;">Nenhuma ocorrência encontrada.</p>';
                return;
            }

            let html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Protocolo</th>
                            <th>Título</th>
                            <th>Cidadão</th>
                            <th style="min-width: 150px;">Local</th>
                            ${currentRole==='admin' ? '<th>Secretaria</th>' : ''}
                            <th>Data</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            list.forEach(o => {
                const s = o.status.toLowerCase();
                const isPanic = o.titulo && (o.titulo.toLowerCase().includes('pânico') || o.titulo.toLowerCase().includes('panico'));
                const isGCM = isPanic || (o.secretaria_nome && (o.secretaria_nome.toLowerCase().includes('guarda') || o.secretaria_nome.toLowerCase().includes('gcm') || o.secretaria_nome.toLowerCase().includes('segurança') || o.secretaria_nome.toLowerCase().includes('seguranca')));
                const hasFichaData = o.ficha_policial && (o.ficha_policial.vitima_nome || o.ficha_policial.descricao_detalhada || o.ficha_policial.agentes_envolvidos);

                const user = getUserInfo();
                const userSecName = (user && user.secretaria_nome ? user.secretaria_nome : '').toLowerCase();
                const userEmail = (user && user.email ? user.email : '').toLowerCase();
                const isSecMulher = currentSecId === 16 || userSecName.includes('mulher') || userSecName.includes('patrulha') || userEmail.includes('patrulhamariadapenha');

                const printBtn = `<button class="btn btn-outline" title="Imprimir" onclick="imprimirProtocolo('${o.id}')"><i class="fa-solid fa-print"></i></button>`;
                
                let updateBtnText = 'Atualizar';
                if (s === 'resolvido') updateBtnText = 'Ver/Editar Ficha';
                else if (isGCM || isSecMulher) updateBtnText = 'Preencher Ficha';
                
                const updateBtn = (s === 'resolvido' && !isGCM && !isSecMulher && !hasFichaData) ? '' : `<button class="btn btn-primary" onclick="openResponseModal('${o.id}', '${encodeURIComponent(o.titulo)}', '${encodeURIComponent(o.secretaria_nome || '')}')">${updateBtnText}</button>`;
                const statusBtn = `<div style="display: flex; gap: 5px;">${printBtn}${updateBtn}</div>`;

                html += `
                    <tr>
                        <td><strong>${o.protocolo || o.id}</strong></td>
                        <td>${o.titulo}</td>
                        <td style="font-weight: 600; color: var(--primary);">${o.usuario_nome || 'N/A'}</td>
                        <td style="font-size: 0.85rem;">
                            ${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}
                            ${o.latitude != null && o.longitude != null ? `<br><a href="javascript:void(0)" onclick="openAdminMap('${o.latitude}', '${o.longitude}', '${encodeURIComponent(o.titulo)}')" style="color: #10b981; font-weight: 600; text-decoration: none; font-size: 0.75rem; display: inline-block; margin-top: 4px;"><i class="fa-solid fa-location-dot"></i> Ver no Mapa</a>` : ''}
                        </td>
                        ${currentRole==='admin' ? `<td>${o.secretaria_nome || 'N/A'}</td>` : ''}
                        <td>${new Date(o.data).toLocaleString()}</td>
                        <td><span class="badge badge-${s === 'resolvido' ? 'done' : (s === 'em_atendimento' ? 'progress' : (s === 'cancelado' ? 'danger' : 'pending'))}">${o.status}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                ${statusBtn}
                                <button class="btn btn-outline" title="Ver Detalhes" onclick="alert(decodeURIComponent('${encodeURIComponent(o.descricao || '')}'))"><i class="fa-solid fa-eye"></i></button>
                                ${o.latitude && o.longitude ? `<button class="btn btn-outline" title="Ver no Mapa" style="border-color: #10b981; color: #10b981;" onclick="openAdminMap('${o.latitude}', '${o.longitude}', '${encodeURIComponent(o.titulo)}')"><i class="fa-solid fa-location-dot"></i></button>` : ''}
                                ${o.foto ? `<button class="btn btn-outline" title="Ver Foto" onclick="window.open('${MEDIA_URL}/${o.foto.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid fa-image"></i></button>` : ''}
                                ${o.video ? `<button class="btn btn-outline" title="Ver Vídeo" onclick="window.open('${MEDIA_URL}/${o.video.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid fa-video"></i></button>` : ''}
                                ${o.documento ? `<button class="btn btn-outline" title="Ver PDF" style="border-color: #8b5cf6; color: #8b5cf6;" onclick="window.open('${MEDIA_URL}/${o.documento.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid fa-file-pdf"></i></button>` : ''}
                                ${currentRole==='admin' ? `<button class="btn btn-outline" title="Excluir Ocorrência" style="border-color: #ef4444; color: #ef4444;" onclick="deletarOcorrencia('${o.id}')"><i class="fa-solid fa-trash"></i></button>` : ''}
                                ${currentRole==='admin' && s !== 'resolvido' ? `<button class="btn" style="background-color: #ef4444; color: white; border: none; font-weight: bold; margin-left: 8px; padding: 6px 12px; border-radius: 6px; box-shadow: 0 2px 5px rgba(239, 68, 68, 0.4); display: flex; align-items: center; gap: 5px;" title="Cobrar Secretaria URGENTE" onclick="cobrarSecretaria('${o.id}')"><i class="fa-solid fa-bell fa-shake"></i> Cobrar</button>` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) { console.error("Error loading ocorrencias:", e); }
}

// ... Additional list loaders (Agendamentos, Users, Admins, Logs) follow similar patterns ...

function openResponseModal(id, title, secNome = '') {
    if (title.includes('%')) title = decodeURIComponent(title);
    if (secNome.includes('%')) secNome = decodeURIComponent(secNome);

    document.getElementById('modalResponseTitle').innerText = `Atualizar #${id}`;
    document.getElementById('modalResponseSubtitle').innerText = title;
    document.getElementById('respText').value = "";
    
    const oc = (currentLoadedOcorrencias || []).find(item => item.id == id);
    const user = getUserInfo();
    const userSecName = (user && user.secretaria_nome ? user.secretaria_nome : '').toLowerCase();
    const userEmail = (user && user.email ? user.email : '').toLowerCase();
    const isSecMulherUser = currentSecId === 16 || userSecName.includes('mulher') || userSecName.includes('patrulha') || userEmail.includes('patrulhamariadapenha');
    const isPanicTitle = title.toLowerCase().includes('pânico') || title.toLowerCase().includes('panico');
    const isGCM = isPanicTitle || secNome.toLowerCase().includes('guarda') || secNome.toLowerCase().includes('gcm') || secNome.toLowerCase().includes('segurança') || secNome.toLowerCase().includes('seguranca');
    
    const fichaContainer = document.getElementById('fichaPolicialContainer');
    const printBtn = document.getElementById('btnPrintFicha');
    
    if (fichaContainer) {
        if (isGCM || isSecMulherUser) {
            fichaContainer.style.display = 'block';
            fichaContainer.dataset.hasFicha = 'true';
            if (document.getElementById('respStatus')) document.getElementById('respStatus').value = 'resolvido';
            const modalBox = document.getElementById('modalResponseCard');
            if (modalBox) {
                modalBox.style.maxWidth = window.innerWidth > 768 ? 'calc(100% - 300px)' : '95%';
                modalBox.style.marginLeft = window.innerWidth > 768 ? '280px' : '0';
            }
            if (printBtn) {
                printBtn.style.display = 'block';
                printBtn.onclick = () => imprimirFichaPolicial(id);
            }

            // Pre-fill existing ficha fields if available
            if (oc && oc.ficha_policial) {
                const fp = oc.ficha_policial;
                const setVal = (fieldId, val) => {
                    const el = document.getElementById(fieldId);
                    if (el && val !== undefined && val !== null) el.value = val;
                };
                setVal('fp_data_fato', fp.data_fato);
                setVal('fp_hora_fato', fp.hora_fato);
                setVal('fp_hora_registro', fp.hora_registro);
                setVal('fp_tipo_ocorrencia_outro', fp.tipo_ocorrencia_outro);
                setVal('fp_vitima_nome', fp.vitima_nome || (oc.usuario_nome || ''));
                setVal('fp_vitima_cpf_rg', fp.vitima_cpf_rg);
                setVal('fp_vitima_data_nascimento', fp.vitima_data_nascimento);
                setVal('fp_vitima_endereco', fp.vitima_endereco || (oc.rua || ''));
                setVal('fp_vitima_telefone', fp.vitima_telefone);
                setVal('fp_suspeito_nome', fp.suspeito_nome);
                setVal('fp_suspeito_apelido', fp.suspeito_apelido);
                setVal('fp_suspeito_cpf_rg', fp.suspeito_cpf_rg);
                setVal('fp_suspeito_data_nascimento', fp.suspeito_data_nascimento);
                setVal('fp_suspeito_endereco', fp.suspeito_endereco);
                setVal('fp_suspeito_caracteristicas', fp.suspeito_caracteristicas);
                setVal('fp_objetos_envolvidos', fp.objetos_envolvidos);
                setVal('fp_descricao_detalhada', fp.descricao_detalhada || (oc.descricao || ''));
                setVal('fp_uso_algemas', fp.uso_algemas);
                setVal('fp_uso_algemas_justificativa', fp.uso_algemas_justificativa);
                setVal('fp_emprego_forca', fp.emprego_forca);
                setVal('fp_emprego_forca_tipo', fp.emprego_forca_tipo);
                setVal('fp_emprego_forca_justificativa', fp.emprego_forca_justificativa);
                setVal('fp_providencias_gcm', fp.providencias_gcm);
                setVal('fp_agentes_envolvidos', fp.agentes_envolvidos);
                setVal('fp_viatura', fp.viatura);
                setVal('fp_encaminhamento', fp.encaminhamento);
                setVal('fp_agente_responsavel', fp.agente_responsavel);
                setVal('fp_comandante_geral', fp.comandante_geral);
                if (fp.tipo_ocorrencia) {
                    const radio = document.querySelector(`input[name="fp_tipo_ocorrencia"][value="${fp.tipo_ocorrencia}"]`);
                    if (radio) radio.checked = true;
                }
            } else if (oc) {
                const setVal = (fieldId, val) => {
                    const el = document.getElementById(fieldId);
                    if (el && val !== undefined && val !== null) el.value = val;
                };
                setVal('fp_vitima_nome', oc.usuario_nome || '');
                setVal('fp_vitima_endereco', oc.rua || '');
                setVal('fp_descricao_detalhada', oc.descricao || '');
            }
        } else {
            fichaContainer.style.display = 'none';
            fichaContainer.dataset.hasFicha = 'false';
            const modalBox = document.getElementById('modalResponseCard');
            if (modalBox) {
                modalBox.style.maxWidth = '600px';
                modalBox.style.marginLeft = '0';
            }
            if (printBtn) printBtn.style.display = 'none';
        }
    }

    document.getElementById('modalResponse').style.display = 'flex';
    
    document.getElementById('btnConfirmResp').onclick = () => confirmResolution(id);
}

async function confirmResolution(id) {
    const fichaContainer = document.getElementById('fichaPolicialContainer');
    const isFichaActive = fichaContainer && fichaContainer.dataset.hasFicha === 'true';

    let resp = document.getElementById('respText') ? document.getElementById('respText').value : '';
    if (!resp) {
        if (isFichaActive) {
            resp = "Ficha de Ocorrência Policial (GCM) preenchida e finalizada.";
        } else {
            return alert("Por favor, digite uma resposta para o cidadão.");
        }
    }
    
    const formData = new FormData();
    formData.append('resposta', resp);
    
    const fotoInput = document.getElementById('respFoto');
    if (fotoInput && fotoInput.files.length > 0) {
        formData.append('foto_resolucao', fotoInput.files[0]);
    }
    const selStatus = isFichaActive ? 'resolvido' : (document.getElementById('respStatus') ? document.getElementById('respStatus').value : 'resolvido');
    
    if (isFichaActive) {
        formData.append('has_ficha', 'true');
        
        const textFields = ['fp_data_fato', 'fp_hora_fato', 'fp_hora_registro', 'fp_tipo_ocorrencia_outro', 'fp_vitima_nome', 'fp_vitima_cpf_rg', 'fp_vitima_data_nascimento', 'fp_vitima_endereco', 'fp_vitima_telefone', 'fp_suspeito_nome', 'fp_suspeito_apelido', 'fp_suspeito_cpf_rg', 'fp_suspeito_data_nascimento', 'fp_suspeito_endereco', 'fp_suspeito_caracteristicas', 'fp_objetos_envolvidos', 'fp_descricao_detalhada', 'fp_uso_algemas', 'fp_uso_algemas_justificativa', 'fp_emprego_forca', 'fp_emprego_forca_tipo', 'fp_emprego_forca_justificativa', 'fp_providencias_gcm', 'fp_agentes_envolvidos', 'fp_viatura', 'fp_encaminhamento', 'fp_agente_responsavel', 'fp_comandante_geral'];
        
        textFields.forEach(field => {
            const el = document.getElementById(field);
            if (el) formData.append(field, el.value);
        });
        
        // Handle radio button for tipo_ocorrencia
        const tipoRadio = document.querySelector('input[name="fp_tipo_ocorrencia"]:checked');
        if (tipoRadio) formData.append('fp_tipo_ocorrencia', tipoRadio.value);
    }
    
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=${selStatus}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        if (res.ok) {
            closeModal('modalResponse');
            if (document.getElementById('respFoto')) document.getElementById('respFoto').value = "";
            
            // Clear ficha fields
            if (fichaContainer) {
                const inputs = fichaContainer.querySelectorAll('input[type="text"], input[type="date"], input[type="time"], textarea, select');
                inputs.forEach(i => i.value = '');
                const radios = fichaContainer.querySelectorAll('input[type="radio"]');
                radios.forEach(r => r.checked = false);
            }

            loadOcorrencias();
            loadDashboard();
            alert("Resposta enviada com sucesso!");
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Erro ao resolver: " + (err.detail || res.statusText));
        }
    } catch(e) { alert("Erro de conexão: " + e.message); }
}

async function deletarOcorrencia(id) {
    if(!confirm("Tem certeza que deseja excluir esta ocorrência permanentemente? Esta ação não pode ser desfeita.")) return;
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Excluído', text: 'Ocorrência excluída com sucesso.', timer: 1500});
            loadOcorrencias();
            loadDashboard();
        } else {
            const err = await res.json().catch(()=>({}));
            Swal.fire({icon: 'error', title: 'Erro', text: err.detail || 'Erro ao excluir.'});
        }
    } catch(e) {
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
}

async function cobrarSecretaria(id) {
    if (!confirm("Deseja enviar um alerta SMS para a secretaria responsável cobrando uma resolução rápida?")) return;
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/cobrar`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            alert("Alerta de cobrança enviado com sucesso para a secretaria!");
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Erro ao enviar alerta: " + (err.detail || res.statusText));
        }
    } catch(e) {
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
}

async function imprimirProtocolo(id) {
    // Reusing the same printing logic from main.js but with clean styles
    try {
        const res = await fetch(`${API_URL}/ocorrencias`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if(res.ok) {
            const data = await res.json();
            const o = data.find(i => i.id == id);
            if (!o) return;
            
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>Protocolo - PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA -AL - ${o.protocolo}</title>
                    <style>
                        body { font-family: 'Inter', sans-serif; padding: 40px; line-height: 1.6; color: #1e293b; }
                        .header { text-align: center; margin-bottom: 40px; border-bottom: 4px solid #2563eb; padding-bottom: 20px; }
                        .content { background: #f8fafc; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; }
                        .row { display: flex; margin-bottom: 15px; }
                        .label { width: 140px; font-weight: 700; color: #64748b; }
                        .stamp { margin-top: 40px; text-align: right; }
                        .badge { padding: 10px 20px; border: 2px solid #10b981; color: #10b981; font-weight: 800; border-radius: 8px; display: inline-block; transform: rotate(-5deg); }
                        @media print { .no-print { display: none; } }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <img src="images/logo-prefeitura.png" alt="Logo Prefeitura" style="max-height: 220px; max-width: 100%; object-fit: contain; margin-bottom: 1.5rem;"><br>
                        <h1>📌 CERTIFICADO DE CONCLUSÃO</h1>
                        <p>PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA - AL</p>
                    </div>
                    <div class="content">
                        <div class="row"><span class="label">PROTOCOLO:</span> <strong>${o.protocolo}</strong></div>
                        <div class="row"><span class="label">CIDADÃO:</span> ${o.usuario_nome || 'N/A'}</div>
                        <div class="row"><span class="label">ASSUNTO:</span> ${o.titulo}</div>
                        <div class="row"><span class="label">LOCAL:</span> ${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}</div>
                        <div class="row"><span class="label">DATA:</span> ${new Date(o.data).toLocaleString()}</div>
                        <div class="row"><span class="label">SITUAÇÃO:</span> ${o.status.toUpperCase()}</div>
                        
                        ${o.foto ? `
                            <div style="margin-top: 15px; text-align: center;">
                                <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 5px;">FOTO ENVIADA PELO CIDADÃO:</p>
                                <img src="${MEDIA_URL}/${o.foto}" style="max-width: 100%; border-radius: 8px; border: 1px solid #e2e8f0;">
                            </div>
                        ` : ''}

                        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                        <div>
                            <span class="label">RESPOSTA ADM:</span>
                            <p>${(o.respostas && o.respostas.length > 0) ? o.respostas[o.respostas.length-1].mensagem : (o.status.toLowerCase() === 'resolvido' ? 'Serviço concluído com sucesso.' : 'Aguardando atendimento.')}</p>
                            ${o.foto_resolucao ? `
                                <div style="margin-top: 15px; text-align: center;">
                                    <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 5px;">FOTO DA SOLUÇÃO:</p>
                                    <img src="${MEDIA_URL}/${o.foto_resolucao}" style="max-width: 100%; border-radius: 8px; border: 1px solid #e2e8f0;">
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="stamp"><div class="badge">${o.status.toLowerCase() === 'resolvido' ? 'SERVIÇO FINALIZADO' : 'SERVIÇO PENDENTE'}</div></div>
                    <div style="text-align: center; margin-top: 40px;">
                        <button onclick="window.print()" class="no-print" style="padding: 10px 30px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Imprimir</button>
                    </div>
                </body>
                </html>
            `);
            printWindow.document.close();
        }
    } catch(e) {}
}

function openModal(id) { document.getElementById(id).style.display = 'flex'; }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }
function logout() { localStorage.clear(); window.location.href = '/admin/index.html'; }

async function loadAgendamentos() {
    try {
        const res = await fetch(`${API_URL}/agendamentos`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            let list = await res.json();
            const userInfo = getUserInfo();
            if (userInfo && userInfo.email === 'denilmalucass@gmail.com') {
                list = list.filter(a => a.assunto && a.assunto.toUpperCase().includes('HOSPITAL MARIA LOUREIRO'));
            } else if (userInfo && userInfo.email === 'ana.gabriela_2@hotmail.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('BELO JARDIM')) || (a.posto && a.posto.toUpperCase().includes('BELO JARDIM')));
            } else if (userInfo && userInfo.email === 'cassianub12@icloud.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('DANIEL MONTEIRO')) || (a.posto && a.posto.toUpperCase().includes('DANIEL MONTEIRO')));
            } else if (userInfo && userInfo.email === 'flaviadanielly381@gmail.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('ADAMOR')) || (a.posto && a.posto.toUpperCase().includes('ADAMOR')));
            } else if (userInfo && userInfo.email === 'vivianlmk@hotmail.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('LUIZ LESSA')) || (a.posto && a.posto.toUpperCase().includes('LUIZ LESSA')));
            } else if (userInfo && userInfo.email === 'ketlinandrade01@icloud.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('VILA NOVA')) || (a.posto && a.posto.toUpperCase().includes('VILA NOVA')));
            } else if (userInfo && userInfo.email === 'trajanojuliana17@gmail.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('TAQUARA')) || (a.posto && a.posto.toUpperCase().includes('TAQUARA')));
            } else if (userInfo && userInfo.email === 'arianacarater@gmail.com') {
                list = list.filter(a => (a.assunto && a.assunto.toUpperCase().includes('ACIOLY')) || (a.posto && a.posto.toUpperCase().includes('ACIOLY')));
            } else if (userInfo && userInfo.email === 'vanuzasoares667@gmail.com') {
                list = list.filter(a => (a.assunto && (a.assunto.toUpperCase().includes('POSTO CENTRO') || a.assunto.toUpperCase().includes('PSF 02'))) || (a.posto && (a.posto.toUpperCase().includes('CENTRO') || a.posto.toUpperCase().includes('PSF 02'))));
            } else if (currentSecId) {
                list = list.filter(a => parseInt(a.secretaria_id) === parseInt(currentSecId));
            }
            list = list.filter(a => a.tipo !== 'Concurso');
            
            const container = document.getElementById('agendamentosTableContainer');
            if (list.length === 0) {
                container.innerHTML = '<p style="padding: 2rem; text-align: center;">Nenhum agendamento encontrado.</p>';
                return;
            }

            let html = `<table class="data-table"><thead><tr><th>Protocolo</th><th>Senha</th><th>Assunto</th><th>Cidadão</th><th>Data/Hora</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(a => {
                const s = a.status.toLowerCase();
                const isEmergencia = a.assunto && a.assunto.includes('EMERGÊNCIA');
                
                let anexosButtons = '';
                if (a.anexo) {
                    const files = a.anexo.split(',');
                    files.forEach((file, index) => {
                        const trimFile = file.trim();
                        if (!trimFile) return;
                        const isImg = trimFile.match(/\.(jpeg|jpg|gif|png|webp)/i);
                        const icon = isImg ? 'fa-image' : 'fa-file-pdf';
                        const title = isImg ? 'Ver Foto' : 'Ver PDF';
                        const colorStyle = isImg ? 'border-color: #a855f7; color: #a855f7;' : 'border-color: #8b5cf6; color: #8b5cf6;';
                        anexosButtons += `<button class="btn btn-outline" title="${title}" style="${colorStyle}" onclick="window.open('${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid ${icon}"></i></button>`;
                    });
                }

                const assuntoLabel = isEmergencia ? `<span style="background-color: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; display: inline-block; animation: pulse 2s infinite; margin-right: 5px;"><i class="fa-solid fa-truck-medical"></i> EMERGÊNCIA</span> ${a.assunto}` : a.assunto;
                const rowClass = isEmergencia ? 'class="emergency-row"' : '';

                html += `
                    <tr ${rowClass}>
                        <td><strong class="${isEmergencia ? 'emergency-protocol' : ''}">${a.protocolo || a.id}</strong></td>
                        <td><span style="font-weight: bold; color: var(--primary);">${a.senha || '---'}</span></td>
                        <td>
                            ${assuntoLabel}
                            ${a.motivo ? `<div style="font-size: 0.8rem; color: #ef4444; margin-top: 4px; font-weight: 500; white-space: pre-line;"><i class="fa-solid fa-notes-medical"></i> <strong>Sintomas:</strong> ${a.motivo}</div>` : ''}
                        </td>
                        <td>${a.usuario_nome || 'N/A'}</td>
                        <td>${new Date(a.data_hora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' })} ${new Date(a.data_hora).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false })}</td>
                        <td><span class="badge badge-${s === 'confirmado' ? 'done' : (s === 'cancelado' ? 'danger' : 'pending')}">${a.status}</span></td>
                        <td>
                            <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                                ${a.cartao_sus ? `<div style="font-size: 0.75rem; color: var(--primary); font-weight: 600;"><i class="fa-solid fa-address-card"></i> SUS: ${a.cartao_sus}</div>` : ''}
                                <div style="display: flex; gap: 0.5rem;">
                                    ${s === 'pendente' ? `<button class="btn btn-primary" onclick="updateAgendamento('${a.id}', 'Confirmado')">Confirmar</button>` : ''}
                                    <button class="btn btn-outline" title="Imprimir Recibo" onclick="imprimirAgendamento('${a.id}')"><i class="fa-solid fa-print"></i></button>
                                    ${anexosButtons}
                                    ${!currentSecId ? `<button class="btn btn-outline" title="Excluir Agendamento" style="border-color: #ef4444; color: #ef4444;" onclick="deletarAgendamento('${a.id}')"><i class="fa-solid fa-trash"></i></button>` : ''}
                                </div>
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {
        console.error("Error loading agendamentos:", e);
    }
}

async function loadConcursos() {
    try {
        const user = getUserInfo();
        const isCulturaEsporte = currentRole === 'admin' || (currentRole === 'subadmin' && user && user.secretaria_nome && user.secretaria_nome.toUpperCase().includes('CULTURA'));
        const uploadContainer = document.getElementById('concursosUploadContainer');
        if (uploadContainer) {
            uploadContainer.style.display = isCulturaEsporte ? 'block' : 'none';
        }

        const btnImprimir = document.getElementById('btnImprimirCamisas');
        if (btnImprimir) {
            btnImprimir.style.display = isCulturaEsporte ? 'inline-flex' : 'none';
        }

        const res = await fetch(`${API_URL}/agendamentos`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            let list = await res.json();
            if (currentSecId) list = list.filter(a => parseInt(a.secretaria_id) === parseInt(currentSecId));
            list = list.filter(a => a.tipo === 'Concurso');
            
            window.todasInscricoes = list;
            
            const container = document.getElementById('concursosTableContainer');
            if (list.length === 0) {
                container.innerHTML = '<p style="padding: 2rem; text-align: center;">Nenhuma inscrição encontrada.</p>';
                return;
            }

            let html = `<table class="data-table"><thead><tr><th>Inscrição</th><th>Protocolo</th><th>Inscrito</th><th>Assunto / Categoria</th><th>Data da Inscrição</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(a => {
                const s = a.status.toLowerCase();
                
                let anexosButtons = '';
                if (a.anexo) {
                    const files = a.anexo.split(',');
                    files.forEach((file, index) => {
                        const trimFile = file.trim();
                        if (!trimFile) return;
                        const isImg = trimFile.match(/\.(jpeg|jpg|gif|png|webp)/i);
                        const icon = isImg ? 'fa-image' : 'fa-file-pdf';
                        const title = isImg ? 'Ver Foto' : 'Ver PDF';
                        const colorStyle = isImg ? 'border-color: #a855f7; color: #a855f7;' : 'border-color: #8b5cf6; color: #8b5cf6;';
                        anexosButtons += `<button class="btn btn-outline" title="${title}" style="${colorStyle}" onclick="window.open('${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid ${icon}"></i></button>`;
                    });
                }

                html += `
                    <tr>
                        <td><span style="font-weight: bold; color: #a855f7; font-size: 1.1rem;">${a.senha || '---'}</span></td>
                        <td><small>${a.protocolo || a.id}</small></td>
                        <td style="font-weight: bold; color: var(--primary);">${a.usuario_nome || 'N/A'}</td>
                        <td>
                            ${a.assunto}
                            ${a.motivo ? `<div style="font-size: 0.85rem; color: #a855f7; margin-top: 5px; font-weight: 500; white-space: pre-line;"><i class="fa-solid fa-id-card"></i> <strong>Dados Extra:</strong><br>${a.motivo}</div>` : ''}
                        </td>
                        <td>${new Date(a.data_hora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' })} ${new Date(a.data_hora).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false })}</td>
                        <td><span class="badge badge-${s === 'confirmado' ? 'done' : (s === 'cancelado' ? 'danger' : 'pending')}">${a.status}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                ${s === 'pendente' ? `<button class="btn btn-primary" style="background: #a855f7; border-color: #a855f7;" onclick="abrirModalConfirmacaoInscricao('${a.id}')">Confirmar</button>` : ''}
                                <button class="btn btn-outline" title="Visualizar Detalhes" style="border-color: #64748b; color: #64748b;" onclick="alert('Detalhes da Inscrição:\\n\\nInscrito: ${a.usuario_nome}\\nProtocolo: ${a.protocolo}\\nAssunto: ${a.assunto.replace(/'/g, "\\'")}\\n\\nMotivo/Dados Extra:\\n${(a.motivo || 'Nenhum').replace(/'/g, "\\'")}\\n\\nAnexos:\\n${a.anexo ? 'Sim (Clique nos botões de foto/pdf para ver)' : 'Nenhuma foto ou documento anexado nesta inscrição.'}')"><i class="fa-solid fa-eye"></i></button>
                                <button class="btn btn-outline" title="Imprimir Comprovante" onclick="imprimirAgendamento('${a.id}')"><i class="fa-solid fa-print"></i></button>
                                <button class="btn btn-outline" style="border-color: #3b82f6; color: #3b82f6;" title="Imprimir Documentação" onclick="imprimirDocumentacao('${a.id}')"><i class="fa-solid fa-images"></i> Imprimir Documentação</button>
                                ${anexosButtons}
                                ${!currentSecId ? `<button class="btn btn-outline" title="Excluir Inscrição" style="border-color: #ef4444; color: #ef4444;" onclick="deletarAgendamento('${a.id}')"><i class="fa-solid fa-trash"></i></button>` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {
        console.error("Error loading concursos:", e);
    }
}
async function deletarAgendamento(id) {
    const result = await Swal.fire({title: 'Atenção', text: 'TEM CERTEZA que deseja excluir esta inscrição/agendamento? Esta ação é IRREVERSÍVEL!', icon: 'warning', showCancelButton: true, confirmButtonText: 'Sim, Excluir', cancelButtonText: 'Cancelar'}); if (!result.isConfirmed) return;
    try {
        const res = await fetch(`${API_URL}/agendamentos/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok || res.status === 204) {
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'Inscrição/Agendamento excluído com sucesso!'});
            loadAgendamentos();
            loadConcursos();
            loadDashboard();
        } else {
            Swal.fire({icon: 'error', title: 'Erro', text: 'Erro ao excluir.'});
        }
    } catch(e) { Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'}); }
}

async function updateOcorrenciaStatus(id, status) {
    const result = await Swal.fire({title: 'Atenção', text: `Mudar status para ${status}?`, icon: 'warning', showCancelButton: true, confirmButtonText: 'Sim', cancelButtonText: 'Não'}); if (!result.isConfirmed) return;
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=${status}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'Status atualizado!'});
            loadOcorrencias();
            loadDashboard();
        } else {
            Swal.fire({icon: 'error', title: 'Erro', text: 'Erro ao atualizar status.'});
        }
    } catch(e) { Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'}); }
}

async function resolveOcorrencia(id) {
    const resp = prompt("Digite a resposta ou parecer para o cidadão:");
    if (resp === null) return;
    
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=Resolvido&resposta=${encodeURIComponent(resp)}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'Ocorrência resolvida com sucesso!'});
            loadOcorrencias();
            loadDashboard();
        } else {
            Swal.fire({icon: 'error', title: 'Erro', text: 'Erro ao resolver ocorrência.'});
        }
    } catch(e) { Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'}); }
}

function abrirModalConfirmacaoInscricao(id) {
    const a = window.todasInscricoes ? window.todasInscricoes.find(i => i.id == id) : null;
    if (!a) {
        Swal.fire({icon: 'warning', title: 'Atenção', text: 'Inscrição não encontrada na memória. Recarregue a página.'});
        return;
    }
    
    const anexoStr = a.anexo || '';
    const usuarioNome = a.usuario_nome || 'N/A';
    const assunto = a.assunto || 'N/A';

    let anexosHtml = '';
    if (anexoStr) {
        const files = anexoStr.split(',');
        files.forEach(f => {
            const trimFile = f.trim();
            if (!trimFile) return;
            const isImg = trimFile.match(/\.(jpeg|jpg|gif|png|webp)/i);
            if (isImg) {
                anexosHtml += `<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 5px; width: 45%; background: white; text-align: center;"><img src="${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}" style="max-width: 100%; max-height: 250px; border-radius: 4px; cursor: pointer; object-fit: contain;" onclick="window.open(this.src, '_blank')"></div>`;
            } else {
                anexosHtml += `<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; background: #f1f5f9; width: 45%; text-align: center; display: flex; align-items: center; justify-content: center;"><a href="${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}" target="_blank" style="color: #2563eb; font-weight: bold; text-decoration: none;"><i class="fa-solid fa-file-pdf"></i> Ver PDF</a></div>`;
            }
        });
    } else {
        anexosHtml = '<p style="color: #64748b; font-style: italic; width: 100%; text-align: center;">Nenhum documento anexado.</p>';
    }

    const modalId = 'modalConfirmarInscricaoDinamico';
    let modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:9999; display:flex; justify-content:center; align-items:center; backdrop-filter: blur(5px);';
        document.body.appendChild(modal);
    }
    
    modal.innerHTML = `
        <div style="background: #fff; border-radius: 12px; width: 90%; max-width: 700px; max-height: 90vh; overflow-y: auto; padding: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); position: relative;">
            <i class="fa-solid fa-times" style="position: absolute; right: 20px; top: 20px; cursor: pointer; font-size: 1.5rem; color: #64748b;" onclick="document.getElementById('${modalId}').style.display='none'"></i>
            <h2 style="color: #a855f7; margin-top: 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;"><i class="fa-solid fa-clipboard-check"></i> Revisar Inscrição</h2>
            
            <div style="margin-bottom: 20px;">
                <p><strong>Cidadão:</strong> ${usuarioNome}</p>
                <p><strong>Assunto:</strong> ${assunto}</p>
            </div>
            
            <h3 style="color: #1e293b; margin-bottom: 10px; font-size: 1.1rem;">Documentos Anexados (Verifique antes de aprovar)</h3>
            <div style="display: flex; gap: 15px; flex-wrap: wrap; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; justify-content: center;">
                ${anexosHtml}
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end; border-top: 2px solid #e2e8f0; padding-top: 15px;">
                <button onclick="document.getElementById('${modalId}').style.display='none'" class="btn btn-outline" style="background: #f1f5f9; color: #475569; border-color: #cbd5e1;">Cancelar</button>
                <button onclick="imprimirAgendamento('${id}')" class="btn btn-outline" style="background: #3b82f6; color: white; border-color: #3b82f6; font-weight: bold;"><i class="fa-solid fa-print"></i> Imprimir Ficha</button>
                <button onclick="document.getElementById('${modalId}').style.display='none'; imprimirDocumentacao('${id}')" class="btn btn-outline" style="border-color: #3b82f6; color: #3b82f6; font-weight: bold;"><i class="fa-solid fa-images"></i> Imprimir Documentação</button>
                <button onclick="document.getElementById('${modalId}').style.display='none'; executarUpdateAgendamento('${id}', 'Confirmado');" class="btn btn-primary" style="background: #10b981; border-color: #10b981; font-weight: bold;"><i class="fa-solid fa-check"></i> Aprovar Inscrição</button>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
}

async function executarUpdateAgendamento(id, status) {
    try {
        const res = await fetch(`${API_URL}/agendamentos/${id}/status?status=${status}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Inscrição concluída com sucesso!', text: 'O comprovante com os documentos será gerado agora para impressão.', confirmButtonText: 'Ok'});
            loadAgendamentos();
            loadConcursos();
            loadDashboard();
            
            // Imprime automaticamente junto com a confirmação
            imprimirAgendamento(id);
        } else {
            const err = await res.json();
            Swal.fire({icon: 'error', title: 'Falha', text: 'Falha ao atualizar status: ' + (err.detail || '')});
        }
    } catch(e) { 
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'}); 
    }
}

async function updateAgendamento(id, status) {
    if (!confirm(`Deseja alterar o status para ${status}?`)) return;
    try {
        const res = await fetch(`${API_URL}/agendamentos/${id}/status?status=${status}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            alert("Status atualizado com sucesso!");
            loadAgendamentos();
            loadConcursos();
            loadDashboard(); // Update metrics too
        } else {
            const err = await res.json();
            Swal.fire({icon: 'error', title: 'Falha', text: 'Falha ao atualizar status: ' + (err.detail || '')});
        }
    } catch(e) { 
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'}); 
    }
}

async function imprimirAgendamento(id) {
    try {
        const res = await fetch(`${API_URL}/agendamentos`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if(res.ok) {
            const data = await res.json();
            const a = data.find(i => i.id == id);
            if (!a) return;
            
            let parceiroNome = '';
            if (a.assunto) {
                const match = a.assunto.match(/(?:^|\|)\s*parceiro(?:\(a\))?:\s*([^|]+)/i);
                if (match) parceiroNome = match[1].trim();
            }
            
            let secretariaNomeStr = 'N/A';
            try {
                const secRes = await fetch(`${API_URL}/secretarias`);
                if (secRes.ok) {
                    const secs = await secRes.json();
                    const secObj = secs.find(s => s.id == a.secretaria_id);
                    if (secObj) secretariaNomeStr = secObj.nome;
                }
            } catch(err) { console.error(err); }
            
            const isConcurso = a.tipo === 'Concurso';
            const isCulturaEsporte = isConcurso && a.assunto && (
                a.assunto.toLowerCase().includes('papa-cuscuz') || 
                a.assunto.toLowerCase().includes('pé de aço') || 
                a.assunto.toLowerCase().includes('pe de aco')
            );
            const titleText = isConcurso ? 'COMPROVANTE DE INSCRIÇÃO' : 'COMPROVANTE DE AGENDAMENTO';
            const iconHeader = isConcurso ? '🏆' : '📌';
            const dateLabel = isConcurso ? 'DATA DE INSCRIÇÃO:' : 'HORÁRIO MARCADO:';
            
            let statusText = 'CONFIRMADO';
            let statusColor = '#10b981'; // Green
            let stampColor = '#10b981';
            let badgeText = isConcurso ? 'INSCRIÇÃO CONFIRMADA' : 'AGENDAMENTO CONFIRMADO';
            
            if (a.status.toLowerCase() === 'pendente') {
                statusText = 'PENDENTE';
                statusColor = '#d97706'; // Amber-600
                stampColor = '#d97706';
                badgeText = isConcurso ? 'INSCRIÇÃO PENDENTE' : 'AGENDAMENTO PENDENTE';
            } else if (a.status.toLowerCase() === 'cancelado') {
                statusText = 'CANCELADO';
                statusColor = '#dc2626'; // Red-600
                stampColor = '#dc2626';
                badgeText = isConcurso ? 'INSCRIÇÃO CANCELADA' : 'AGENDAMENTO CANCELADO';
            }

            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>${titleText} - ${a.protocolo || a.id}</title>
                    <style>
                        @page { size: A4 portrait; margin: 10mm; }
                        body { font-family: 'Inter', sans-serif; padding: 15px; line-height: 1.35; color: #1e293b; font-size: 0.9rem; margin: 0; }
                        .header { text-align: center; margin-bottom: 15px; border-bottom: 3px solid #10b981; padding-bottom: 10px; }
                        .header img { max-height: 120px; max-width: 100%; object-fit: contain; margin-bottom: 0.5rem; }
                        .header h1 { font-size: 1.3rem; margin: 5px 0; }
                        .header p { font-size: 0.8rem; margin: 0; }
                        .content { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
                        .row { display: flex; margin-bottom: 8px; align-items: flex-start; }
                        .label { width: 140px; font-weight: 700; color: #64748b; font-size: 0.85rem; }
                        .stamp { margin-top: 15px; text-align: right; }
                        .badge { padding: 6px 14px; border: 2px solid ${stampColor}; color: ${stampColor}; font-weight: 800; border-radius: 6px; display: inline-block; transform: rotate(-3deg); font-size: 0.85rem; }
                        @media print { 
                            .no-print { display: none !important; } 
                            body { padding: 0; }
                            .content { background: #ffffff !important; border: 1px solid #cbd5e1 !important; }
                        }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <img src="images/logo-prefeitura.png" alt="Logo Prefeitura"><br>
                        ${isCulturaEsporte ? `<img src="imagens/logo-cultura-esporte.png" alt="Logo Cultura" style="max-height: 90px; margin-bottom: 0.5rem;"><br>` : ''}
                        <h1>${iconHeader} ${titleText}</h1>
                        <p>PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA - AL</p>
                    </div>
                    <div class="content">
                        <div class="row"><span class="label">PROTOCOLO:</span> <strong>${a.protocolo || a.id}</strong></div>
                        ${a.senha ? `<div class="row"><span class="label" style="color: #2563eb;">${isConcurso ? 'Nº DE INSCRIÇÃO:' : 'SENHA:'}</span> <strong style="font-size: 1.2rem; color: #2563eb;">${a.senha}</strong></div>` : ''}
                        <div class="row"><span class="label">CIDADÃO:</span> <strong>${a.usuario_nome || 'N/A'}${isConcurso && parceiroNome ? ` e ${parceiroNome}` : ''}</strong></div>
                        <div class="row"><span class="label">ENDEREÇO:</span> ${a.usuario_endereco || 'Não informado'}</div>
                        ${parceiroNome ? `<div class="row"><span class="label">PARCEIRO(A):</span> <strong>${parceiroNome}</strong></div>` : ''}
                        <div class="row"><span class="label">SECRETARIA:</span> <strong>${secretariaNomeStr}</strong></div>
                        <div class="row"><span class="label">ASSUNTO:</span> ${a.assunto}</div>
                        ${a.motivo ? `<div class="row" style="white-space: pre-line;"><span class="label">MOTIVO:</span> ${a.motivo}</div>` : ''}
                        ${a.cartao_sus ? `<div class="row"><span class="label">CARTÃO SUS:</span> ${a.cartao_sus}</div>` : ''}
                        ${a.acompanhante ? `<div class="row"><span class="label">ACOMPANHANTE:</span> ${a.acompanhante}</div>` : ''}
                        <div class="row" style="background: #f1f5f9; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;">
                            <span class="label">${dateLabel}</span> 
                            <div style="flex: 1;">
                                <strong style="font-size: 1.2rem; color: #1e293b;">${(() => { const d = new Date(a.data_hora); const od = { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' }; const ot = { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false }; return d.toLocaleDateString('pt-BR', od) + ' às ' + d.toLocaleTimeString('pt-BR', ot) + ' (Horário de Brasília)'; })()}</strong>
                                ${(() => {
                                    const tipoStr = (a.tipo || '').toLowerCase();
                                    const assuntoStr = (a.assunto || '').toLowerCase();
                                    const secStr = (secretariaNomeStr || '').toLowerCase();
                                    const isMaquina = tipoStr.includes('máquina') || tipoStr.includes('maquina') || tipoStr.includes('trator') || tipoStr.includes('açude') || tipoStr.includes('estrada') || assuntoStr.includes('maquina') || assuntoStr.includes('máquina') || assuntoStr.includes('trator') || assuntoStr.includes('arado') || assuntoStr.includes('açude') || assuntoStr.includes('barreiro');
                                    const isAgricultura = secStr.includes('agricultura') || isMaquina;
                                    if (isAgricultura) {
                                        return `<div style="color: #dc2626; font-weight: 800; font-size: 0.9rem; margin-top: 4px; text-transform: uppercase;">⚠️ SUJEITO A ALTERAÇÃO DE DATA DE ACORDO COM AS MANUTENÇÕES EM MAQUINAS</div>`;
                                    }
                                    return '';
                                })()}
                            </div>
                        </div>
                        <div class="row"><span class="label">SITUAÇÃO:</span> <strong style="color: ${statusColor};">${statusText}</strong></div>
                        ${(() => {
                            const tipoStr = (a.tipo || '').toLowerCase();
                            const assuntoStr = (a.assunto || '').toLowerCase();
                            const secStr = (secretariaNomeStr || '').toLowerCase();
                            const isViagem = tipoStr.includes('viagem') || tipoStr.includes('marcação de viagem') || assuntoStr.includes('viagem');
                            const isGaragem = secStr.includes('garagem') || a.secretaria_id == 22 || isViagem;
                            const isMaquina = tipoStr.includes('máquina') || tipoStr.includes('maquina') || tipoStr.includes('trator') || tipoStr.includes('açude') || tipoStr.includes('estrada') || assuntoStr.includes('maquina') || assuntoStr.includes('máquina') || assuntoStr.includes('trator') || assuntoStr.includes('arado') || assuntoStr.includes('açude') || assuntoStr.includes('barreiro');
                            const isAgricultura = secStr.includes('agricultura') || isMaquina;
                            const isConfirmado = a.status && a.status.toLowerCase() === 'confirmado';

                            let avisoHtml = '';
                            if (isGaragem && isViagem && isConfirmado) {
                                avisoHtml += `
                                    <div style="background: #fef2f2; border: 2px dashed #ef4444; border-radius: 12px; padding: 18px 24px; margin-top: 20px; margin-bottom: 10px; text-align: center; box-shadow: 0 2px 8px rgba(239, 68, 68, 0.1);">
                                        <strong style="color: #dc2626; font-size: 1.2rem; display: block; margin-bottom: 6px; text-transform: uppercase;">
                                            ⚠️ ATENÇÃO - CONFIRMAÇÃO DE VIAGEM OBRIGATÓRIA
                                        </strong>
                                        <span style="color: #991b1b; font-weight: 700; font-size: 1.05rem; line-height: 1.5; display: block;">
                                            O CIDADÃO DEVE COMPARECER À GARAGEM MUNICIPAL PARA CONFIRMAR SUA VIAGEM!
                                        </span>
                                    </div>
                                `;
                            }

                            if (isAgricultura) {
                                avisoHtml += `
                                    <div style="background: #f0fdf4; border: 2px dashed #16a34a; border-radius: 12px; padding: 18px 24px; margin-top: 20px; margin-bottom: 10px; text-align: center; box-shadow: 0 2px 8px rgba(22, 163, 74, 0.1);">
                                        <strong style="color: #15803d; font-size: 1.2rem; display: block; margin-bottom: 6px; text-transform: uppercase;">
                                            🚜 ATENÇÃO - CONFIRMAÇÃO DA MÁQUINA AGRÍCOLA
                                        </strong>
                                        <div style="background: #ffffff; border: 1px solid #bbf7d0; border-radius: 8px; padding: 8px 12px; margin: 8px 0; color: #14532d; font-weight: 800; font-size: 1.05rem;">
                                            MÁQUINA SOLICITADA: ${a.tipo || 'Máquina Agrícola'}
                                        </div>
                                        <span style="color: #166534; font-weight: 700; font-size: 1.05rem; line-height: 1.5; display: block; margin-bottom: 8px;">
                                            COMPAREÇA À SECRETARIA DE AGRICULTURA UM DIA ANTES PARA CONFIRMAÇÃO DA MÁQUINA!
                                        </span>
                                        <span style="color: #dc2626; font-weight: 800; font-size: 0.95rem; display: block; text-transform: uppercase;">
                                            ⚠️ SUJEITO A ALTERAÇÃO DE DATA DE ACORDO COM AS MANUTENÇÕES EM MAQUINAS
                                        </span>
                                    </div>
                                `;
                            }
                            return avisoHtml;
                        })()}
                        ${(() => {
                            if (!a.anexo) return '';
                            let anexosHtml = '<div style="margin-top: 20px; page-break-inside: avoid;"><h3 style="border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; color: #1e293b;">Documentos Anexados</h3><div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px;">';
                            const files = a.anexo.split(',');
                            files.forEach(f => {
                                const trimFile = f.trim();
                                if (!trimFile) return;
                                const isImg = trimFile.match(/\.(jpeg|jpg|gif|png|webp)/i);
                                if (isImg) {
                                    anexosHtml += `<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 5px; width: 45%; background: white;"><img src="${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}" style="max-width: 100%; height: auto; border-radius: 4px;"></div>`;
                                } else {
                                    anexosHtml += `<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; background: #f1f5f9; width: 45%;"><a href="${MEDIA_URL}/${trimFile.replace(/\\/g, '/')}" target="_blank" style="color: #2563eb; font-weight: bold; text-decoration: none;">📄 Documento PDF Em Anexo</a></div>`;
                                }
                            });
                            anexosHtml += '</div></div>';
                            return anexosHtml;
                        })()}
                    </div>
                    <div class="stamp"><div class="badge">${badgeText}</div></div>
                    <div style="text-align: center; margin-top: 40px;">
                        <button onclick="window.print()" class="no-print" style="padding: 10px 30px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Imprimir</button>
                    </div>
                </body>
                </html>
            `);
            printWindow.document.close();
        }
    } catch(e) {
        alert("Erro ao gerar impressão.");
    }
}

async function loadUsers() {
    try {
        const res = await fetch(`${ADMIN_API}/users`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            const list = await res.json();
            const container = document.getElementById('usuariosTableContainer');
            
            let html = `<table class="data-table"><thead><tr><th>ID</th><th>Nome</th><th>CPF</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(u => {
                const s = u.status.toLowerCase();
                html += `
                    <tr>
                        <td>#${u.id}</td>
                        <td>${u.nome}</td>
                        <td>${u.cpf}</td>
                        <td><span class="badge badge-${s === 'ativo' ? 'done' : 'pending'}">${u.status}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                ${s === 'pendente' ? `<button class="btn btn-primary" onclick="userAction('${u.id}', 'approve')">Aprovar</button>` : ''}
                                <button class="btn btn-outline" style="color: var(--danger);" onclick="userAction('${u.id}', 'delete')"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {}
}

async function userAction(id, action) {
    if (action === 'delete' && !confirm("Excluir permanentemente?")) return;
    const url = `${ADMIN_API}/users/${id}/${action === 'delete' ? '' : action}`;
    const method = action === 'delete' ? 'DELETE' : 'POST';
    
    try {
        const res = await fetch(url, { method, headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) { loadUsers(); loadDashboard(); }
    } catch(e) { alert("Erro ao processar."); }
}

async function loadAuditLogs() {
    try {
        const res = await fetch(`${ADMIN_API}/metrics/logs`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            const list = await res.json();
            const container = document.getElementById('auditLogsTableContainer');
            
            let html = `<table class="data-table"><thead><tr><th>Data</th><th>Admin</th><th>Ação</th><th>Detalhes</th></tr></thead><tbody>`;
            list.forEach(l => {
                html += `
                    <tr>
                        <td style="font-size: 0.8rem;">${new Date(l.data).toLocaleString()}</td>
                        <td><small>${l.usuario_tipo.toUpperCase()}</small></td>
                        <td><strong>${l.acao}</strong></td>
                        <td><small>${l.detalhes}</small></td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {}
}

async function loadAdmins() {
    try {
        const res = await fetch(`${ADMIN_API}/users/secretaria-admins`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            const list = await res.json();
            const container = document.getElementById('adminsTableContainer');
            
            const btnNew = document.getElementById('btnNewAdminHeader');
            const titleSection = document.getElementById('adminsSectionTitle');
            if (currentRole === 'subadmin') {
                if (btnNew) btnNew.style.display = 'none';
                if (titleSection) titleSection.innerText = 'Equipe da Secretaria';
            } else {
                if (btnNew) btnNew.style.display = 'block';
                if (titleSection) titleSection.innerText = 'Sub-Administradores (Secretarias)';
            }
            
            // Need secretarias map for display
            const sRes = await fetch(`${API_URL}/secretarias`);
            const secs = await sRes.json();
            const sMap = {}; secs.forEach(s => sMap[s.id] = s.nome);
            
            const select = document.getElementById('newAdminSec');
            select.innerHTML = secs.map(s => `<option value="${s.id}">${s.nome}</option>`).join('');

            const postoHealthMap = {
                'denilmalucass@gmail.com': 'HOSPITAL MARIA LOUREIRO (EMERGÊNCIA)',
                'vivianlmk@hotmail.com': 'POSTO JOSÉ LUIZ LESSA (PSF 01)',
                'vanuzasoares667@gmail.com': 'POSTO CENTRO (PSF 02)',
                'ketlinandrade01@icloud.com': 'POSTO VILA NOVA (PSF 03)',
                'cassianub12@icloud.com': 'POSTO DANIEL MONTEIRO DA CRUZ (PSF 04)',
                'trajanojuliana17@gmail.com': 'POSTO DE SAÚDE USINA TAQUARA (PSF 05)',
                'ana.gabriela_2@hotmail.com': 'POSTO BELO JARDIM (PSF 06)',
                'flaviadanielly381@gmail.com': 'POSTO JOSÉ ADAMOR COSTA (PSF 07)',
                'arianacarater@gmail.com': 'POSTO JOSÉ ACIOLY MACIEL (PSF 08)'
            };

            // Order subadmins: Health Posts first, then rest
            list.sort((a, b) => {
                const postoA = postoHealthMap[(a.email || '').toLowerCase()];
                const postoB = postoHealthMap[(b.email || '').toLowerCase()];
                if (postoA && !postoB) return -1;
                if (!postoA && postoB) return 1;
                return (a.nome || '').localeCompare(b.nome || '');
            });

            let html = `<table class="data-table"><thead><tr><th>Nome</th><th>Secretaria / Lotação</th><th>E-mail</th><th>Telefone</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(a => {
                const currentUser = getUserInfo();
                let actionButtons = '';
                
                if (currentRole === 'admin' || (currentRole === 'subadmin' && currentUser && a.id == currentUser.id)) {
                    actionButtons += `
                        <button class="btn btn-primary" style="font-size: 0.7rem; padding: 4px 10px;" onclick="openPasswordModal('${a.id}', 'subadmin', '${a.nome}')"><i class="fa-solid fa-key"></i> Trocar Senha</button>
                    `;
                }
                if (currentRole === 'admin') {
                    actionButtons += `
                        <button class="btn btn-primary" style="background-color: #10b981; border: none; font-size: 0.7rem; padding: 4px 10px;" onclick="changeSubAdminPhone('${a.id}', '${a.telefone || ''}')"><i class="fa-solid fa-phone"></i> Trocar Telefone</button>
                        <button class="btn" style="background-color: #f59e0b; color: white; border: none; font-size: 0.7rem; padding: 4px 10px; border-radius: 6px; display: flex; align-items: center; gap: 4px;" title="Notificar Pendências" onclick="notificarSubAdmin('${a.id}', '${a.nome}')"><i class="fa-solid fa-bell"></i> Notificar</button>
                        <button class="btn btn-outline" style="color: var(--danger); font-size: 0.7rem; padding: 4px 10px;" onclick="deleteAdmin('${a.id}')"><i class="fa-solid fa-trash"></i></button>
                    `;
                }

                const emailLower = (a.email || '').toLowerCase();
                const postoNome = postoHealthMap[emailLower];

                let lotacaoHtml = `<span class="badge badge-progress">${sMap[a.secretaria_id] || 'N/A'}</span>`;
                if (postoNome) {
                    lotacaoHtml += `<div style="margin-top: 4px;"><span style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-user-doctor"></i> ${postoNome}</span></div>`;
                }

                html += `
                    <tr>
                        <td style="font-weight: 600;">${a.nome}</td>
                        <td>${lotacaoHtml}</td>
                        <td>${a.email}</td>
                        <td>${a.telefone || '-'}</td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                ${actionButtons}
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {}
}

async function createSubAdmin(e) {
    e.preventDefault();
    const senha = document.getElementById('newAdminPass').value;
    if (senha.length < 8) return alert('A senha deve ter no mínimo 8 dígitos.');
    if (!/[A-Z]/.test(senha)) return alert('A senha deve conter pelo menos uma letra maiúscula.');
    if (!/[0-9]/.test(senha)) return alert('A senha deve conter pelo menos um número.');
    if (!/[!*#$@%^&+=?_\-\W]/.test(senha)) return alert('A senha deve conter pelo menos um caractere especial (!*#$).');

    const data = {
        nome: document.getElementById('newAdminName').value,
        cpf: document.getElementById('newAdminCPF').value,
        email: document.getElementById('newAdminEmail').value,
        telefone: document.getElementById('newAdminTel').value,
        senha: senha,
        secretaria_id: parseInt(document.getElementById('newAdminSec').value)
    };
    try {
        const res = await fetch(`${ADMIN_API}/users/secretaria-admins`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            document.getElementById('formAdmin').reset();
            closeModal('modalNewAdmin');
            loadAdmins();
            alert("Sub-administrador cadastrado!");
        } else {
            const err = await res.json();
            alert(err.detail || "Erro ao cadastrar.");
        }
    } catch(e) {}
}

async function deleteAdmin(id) {
    if (!confirm("Tem certeza que deseja excluir este sub-administrador?")) return;
    try {
        const res = await fetch(`${ADMIN_API}/users/secretaria-admins/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            loadAdmins();
            loadDashboard();
            alert("Administrador excluído com sucesso.");
        } else {
            const err = await res.json();
            alert(err.detail || "Erro ao excluir administrador.");
        }
    } catch(e) {
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
}

async function loadAllCombinedUsers() {
    try {
        const res = await fetch(`${ADMIN_API}/users/all-combined`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const list = await res.json();
            const container = document.getElementById('allUsersTableContainer');
            const counter = document.getElementById('totalUsersCounter');
            if (counter) counter.innerText = list.length;
            
            let html = `<table class="data-table"><thead><tr><th>Nome</th><th>E-mail</th><th>Telefone / Contato</th><th>Tipo</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(u => {
                const color = u.tipo === 'admin' ? '#ef4444' : (u.tipo === 'subadmin' ? '#f59e0b' : '#22c55e');
                const s = (u.status || 'ativo').toLowerCase();
                const telDisplay = u.telefone || u.whatsapp || 'Não informado';
                const escNome = (u.nome || '').replace(/'/g, "\\'");
                const escTel = telDisplay.replace(/'/g, "\\'");
                
                let panicoBtn = '';
                if (u.source === 'usuario') {
                    const isPanicoAuth = u.botao_panico_autorizado === 1;
                    const panicoColor = isPanicoAuth ? '#10b981' : '#6b7280';
                    const panicoText = isPanicoAuth ? 'Pânico: ON' : 'Pânico: OFF';
                    panicoBtn = `<button class="btn btn-outline" style="color: ${panicoColor}; border-color: ${panicoColor}; font-size: 0.7rem; padding: 4px 10px;" onclick="togglePanicoAuth('${u.id}')"><i class="fa-solid fa-triangle-exclamation"></i> ${panicoText}</button>`;
                }

                html += `
                    <tr>
                        <td><strong>${u.nome}</strong></td>
                        <td>${u.email}</td>
                        <td><span style="font-family: monospace; font-size: 0.85rem;"><i class="fa-solid fa-phone" style="color: #3b82f6; margin-right: 4px;"></i> ${telDisplay}</span></td>
                        <td><span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; background: ${color}20; color: ${color}; font-weight: 600;">${u.tipo.toUpperCase()}</span></td>
                        <td><span class="badge badge-${s === 'ativo' ? 'done' : 'pending'}">${u.status || 'Ativo'}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                                ${panicoBtn}
                                <button class="btn btn-outline" style="border-color: #3b82f6; color: #3b82f6; font-size: 0.7rem; padding: 4px 10px;" onclick="openEditPhoneModal('${u.id}', '${u.source}', '${escNome}', '${escTel}')"><i class="fa-solid fa-pen-to-square"></i> Editar Telefone</button>
                                <button class="btn btn-primary" style="font-size: 0.7rem; padding: 4px 10px;" onclick="openPasswordModal('${u.id}', '${u.source}', '${escNome}')"><i class="fa-solid fa-key"></i> Trocar Senha</button>
                                <button class="btn btn-outline" style="color: var(--danger); font-size: 0.7rem; padding: 4px 10px;" onclick="deleteCombinedUser('${u.id}', '${u.source}')"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch(e) {
        console.error("Error loading all combined users:", e);
    }
}

async function openEditPhoneModal(userId, source, userName, currentPhone) {
    const { value: newPhone } = await Swal.fire({
        title: `Editar Telefone de ${userName}`,
        html: `<p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;">Digite o novo número de telefone/WhatsApp:</p>`,
        input: 'text',
        inputValue: currentPhone && currentPhone !== 'Não informado' ? currentPhone : '',
        inputPlaceholder: '(82) 99999-9999',
        showCancelButton: true,
        confirmButtonText: '<i class="fa-solid fa-floppy-disk"></i> Salvar Telefone',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#3b82f6',
        inputValidator: (val) => {
            if (!val || val.trim().length < 8) {
                return 'Por favor, insira um número de telefone válido com DD!';
            }
        }
    });

    if (newPhone) {
        try {
            const res = await fetch(`${ADMIN_API}/users/${userId}/phone`, {
                method: 'PATCH',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}` 
                },
                body: JSON.stringify({ novo_telefone: newPhone.trim(), source: source })
            });

            if (res.ok) {
                Swal.fire({
                    icon: 'success',
                    title: 'Telefone Atualizado!',
                    text: `O número de telefone foi atualizado com sucesso.`,
                    timer: 1800,
                    showConfirmButton: false
                });
                loadAllCombinedUsers();
            } else {
                const err = await res.json();
                Swal.fire({ icon: 'error', title: 'Erro', text: err.detail || 'Não foi possível atualizar o telefone.' });
            }
        } catch (e) {
            console.error(e);
            Swal.fire({ icon: 'error', title: 'Erro', text: 'Erro de conexão com o servidor.' });
        }
    }
}

async function togglePanicoAuth(userId) {
    try {
        const res = await fetch(`${ADMIN_API}/users/${userId}/panico-auth`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            loadAllCombinedUsers();
            Swal.fire({icon: 'success', title: 'Atualizado', text: 'Permissão do botão do pânico alterada.', timer: 1500, showConfirmButton: false});
        } else {
            const err = await res.json();
            Swal.fire({icon: 'error', title: 'Erro', text: err.detail || 'Erro ao alterar permissão.'});
        }
    } catch (e) {
        console.error(e);
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
}

async function deleteCombinedUser(id, source) {
    if (!confirm("Excluir permanentemente este usuário?")) return;
    const url = source === 'subadmin' ? `${ADMIN_API}/users/secretaria-admins/${id}` : `${ADMIN_API}/users/${id}`;
    try {
        const res = await fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) { loadAllCombinedUsers(); loadDashboard(); }
    } catch(e) { Swal.fire({icon: 'error', title: 'Erro', text: 'Erro ao excluir.'}); }
}

let currentPasswordUserId = '';
let currentPasswordUserSource = '';

function openPasswordModal(id, source, nome) {
    if (!id || id === 'undefined' || id === 'null') {
        Swal.fire({icon: 'error', title: 'Erro Crítico', text: "ID do usuário está vazio ao abrir o modal! ID: " + id});
        return;
    }
    currentPasswordUserId = id;
    currentPasswordUserSource = source;
    document.getElementById('senha_user_id').value = id;
    document.getElementById('senha_user_source').value = source;
    document.getElementById('modalSenhaTitle').innerText = `Alterar Senha: ${nome}`;
    document.getElementById('nova_senha_input').value = '';
    document.getElementById('modalAlterarSenha').style.display = 'block';
}

window.submitAlterarSenha = async function() {
    const id = currentPasswordUserId || document.getElementById('senha_user_id').value;
    const source = currentPasswordUserSource || document.getElementById('senha_user_source').value;
    const new_password = document.getElementById('nova_senha_input').value;

    if (!id || !source) {
        console.warn("Auto-submit evitado: id ou source ausentes.");
        if (document.getElementById('modalAlterarSenha').style.display === 'block') {
             Swal.fire({icon: 'warning', title: 'Atenção', text: "ID ou Source sumiram do formulário. Feche o modal e abra novamente."});
        }
        return;
    }

    if (!new_password) {
        Swal.fire({icon: 'warning', title: 'Atenção', text: "Digite a nova senha."});
        return;
    }

    const btn = document.getElementById('btnConfirmarAlteracaoModal');
    let originalText = 'Confirmar Alteração';
    if (btn) {
        originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Aguarde...';
        btn.disabled = true;
    }

    try {
        const res = await fetch(`${ADMIN_API}/users/password-reset`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify({
                user_id: id,
                source: source,
                new_password: new_password
            })
        });

        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'Senha alterada com sucesso.'});
            document.getElementById('modalAlterarSenha').style.display = 'none';
        } else {
            const err = await res.json().catch(() => ({}));
            const errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail || "Erro desconhecido.");
            Swal.fire({icon: 'error', title: 'Falha', text: "Erro ao alterar senha: " + errorMsg});
        }
    } catch(err) {
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão: ' + err.message});
    } finally {
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
};

// Admin self-password update (from config section)
async function updatePassword(e) {
    if (e) e.preventDefault();
    const current = document.getElementById('pwCurrent').value;
    const newPw = document.getElementById('pwNew').value;
    const confirm = document.getElementById('pwConfirm').value;

    if (!current || !newPw || !confirm) {
        Swal.fire({icon: 'warning', title: 'Atenção', text: 'Por favor, preencha todos os campos de senha.'});
        return;
    }
    if (newPw !== confirm) {
        Swal.fire({icon: 'warning', title: 'Atenção', text: 'A nova senha e a confirmação não coincidem.'});
        return;
    }
    if (newPw.length < 6) {
        Swal.fire({icon: 'warning', title: 'Atenção', text: 'A nova senha deve ter pelo menos 6 caracteres.'});
        return;
    }

    const btn = document.querySelector('button[onclick="updatePassword()"]');
    const originalText = btn ? btn.innerHTML : 'Atualizar Senha';
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Aguarde...';
        btn.disabled = true;
    }

    try {
        const res = await fetch(`${API_URL}/auth/change-password`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ senha_atual: current, nova_senha: newPw })
        });

        if (res.ok) {
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'Senha alterada com sucesso.'});
            document.getElementById('pwCurrent').value = '';
            document.getElementById('pwNew').value = '';
            document.getElementById('pwConfirm').value = '';
        } else {
            const err = await res.json().catch(() => ({}));
            const errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail || "Erro desconhecido.");
            Swal.fire({icon: 'error', title: 'Falha', text: "Erro: " + errorMsg});
        }
    } catch(err) {
        Swal.fire({icon: 'error', title: 'Erro', text: "Erro de conexão: " + err.message});
    } finally {
        const btn = document.querySelector('button[onclick="updatePassword()"]');
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}

// Search ocorrencias by name or protocol
function searchOcorrenciasBtn() {
    const query = document.getElementById('searchOcorrencias').value.trim().toLowerCase();
    filterTable('ocorrenciasTableContainer', query);
}

// Universal Real-time Search Filter for Tables
function filterTable(containerId, query) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const table = container.querySelector('table');
    if (!table) return;
    
    const term = query.toLowerCase().trim();
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const textContext = row.textContent.toLowerCase();
        if (textContext.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

async function notificarSubAdmin(id, nome) {
    if (!confirm(`Deseja enviar agora uma notificação SMS para ${nome} alertando sobre as ocorrências pendentes na secretaria dele?`)) return;
    
    try {
        const res = await fetch(`${ADMIN_API}/users/secretaria-admins/${id}/notificar-pendencias`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (res.ok) {
            const data = await res.json();
            alert(`Sucesso! ${data.message} (${data.count_pending} pendências detectadas)`);
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Erro ao notificar: " + (err.detail || "Falha na comunicação com o servidor."));
        }
    } catch(e) {
        alert("Erro de conexão ao tentar notificar.");
    }
}

// Profile Photo Upload
async function uploadProfilePhoto(input) {
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const btn = document.getElementById('btnChangePhoto');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enviando...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch(`${API_URL}/auth/update-photo`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            // Update local user info
            const user = getUserInfo();
            user.foto_perfil = data.url;
            localStorage.setItem('user_info', JSON.stringify(user));
            
            // Refresh UI
            initAdmin();
            refreshConfigUI();
            alert("Foto de perfil atualizada com sucesso!");
        } else {
            const err = await res.json();
            alert("Erro: " + (err.detail || "Falha no upload"));
        }
    } catch (e) {
        console.error(e);
        alert("Erro de conexão ao enviar foto.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function refreshConfigUI() {
    const user = getUserInfo();
    const configAvatar = document.getElementById('configAvatar');
    if (!configAvatar) return;

    if (user.foto_perfil) {
        const src = user.foto_perfil.startsWith('data:') ? user.foto_perfil : `${MEDIA_URL}${user.foto_perfil}`;
        configAvatar.innerHTML = `<img src="${src}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
    } else {
        configAvatar.innerText = (user.nome || user.email).charAt(0).toUpperCase();
    }

    const inputNome = document.getElementById('configNome');
    if (inputNome) inputNome.value = user.nome || "";
}

async function updateName() {
    const btn = event.target;
    const originalText = btn.innerText;
    const nome = document.getElementById('configNome').value.trim();
    if (!nome) return alert("Por favor, digite um nome.");

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Salvando...';

        const res = await fetch(`${API_URL}/auth/update-name`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ nome })
        });

        if (res.ok) {
            const data = await res.json();
            alert("Nome atualizado com sucesso!");
            
            // Atualizar localmente no localStorage usando a chave correta 'user_info'
            const user = getUserInfo();
            if (user) {
                user.nome = data.nome;
                localStorage.setItem('user_info', JSON.stringify(user));
            }
            
            // Refresh UI do dashboard (topo, etc)
            initAdmin(); 
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Erro: " + (err.detail || "Não foi possível atualizar o nome. Verifique se o backend foi atualizado."));
        }
    } catch(e) {
        alert("Erro de conexão: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

function toggleResetCard() {
    const card = document.getElementById('resetSystemCard');
    if (card) card.style.display = currentRole === 'admin' ? 'block' : 'none';
}

async function resetSystem() {
    const confirm1 = confirm("⚠️ ATENÇÃO: Isto vai APAGAR todas as ocorrências, agendamentos, respostas, chats e logs de auditoria.\n\nUsuários, admins e secretarias serão MANTIDOS.\n\nDeseja continuar?");
    if (!confirm1) return;
    
    const confirm2 = prompt('Digite "ZERAR" para confirmar:');
    if (confirm2 !== 'ZERAR') {
        alert('Operação cancelada. Você precisa digitar ZERAR para confirmar.');
        return;
    }
    
    try {
        const res = await fetch(`${ADMIN_API}/metrics/reset-system`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (res.ok) {
            const data = await res.json();
            alert(`✅ ${data.message}\n\nRemovidos:\n- ${data.removidos.ocorrencias} ocorrências\n- ${data.removidos.agendamentos} agendamentos\n- ${data.removidos.respostas} respostas\n- ${data.removidos.chats} chats\n- ${data.removidos.logs_auditoria} logs`);
            loadDashboard();
        } else {
            const err = await res.json().catch(() => ({}));
            alert('Erro: ' + (err.detail || 'Falha ao zerar o sistema.'));
        }
    } catch(e) {
        alert('Erro de conexão: ' + e.message);
    }
}

async function loadPerformance() {
    const container = document.getElementById('performanceContainer');
    if (container) container.innerHTML = '<p style="text-align:center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Carregando dados...</p>';
    try {
        const res = await fetch(`${ADMIN_API}/metrics/secretaria-performance`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) {
            if (container) container.innerHTML = '<p style="text-align:center; color: #ef4444; padding: 2rem;"><i class="fa-solid fa-circle-exclamation"></i> Erro ao carregar dados. Verifique se o backend foi atualizado.</p>';
            return;
        }
        const data = await res.json();
        
        const container = document.getElementById('performanceContainer');
        if (!container) return;
        
        if (data.length === 0) {
            container.innerHTML = '<p style="text-align:center; color: var(--text-muted); padding: 2rem;">Nenhuma secretaria cadastrada.</p>';
            return;
        }
        
        let html = '';
        data.forEach(s => {
            const taxaColor = s.ocorrencias.taxa_resolucao >= 70 ? '#10b981' : (s.ocorrencias.taxa_resolucao >= 40 ? '#f59e0b' : '#ef4444');
            
            html += `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h4 style="margin: 0;">${s.nome}</h4>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <button class="btn btn-outline" style="font-size: 0.75rem; padding: 4px 10px; border-color: var(--primary); color: var(--primary);" onclick="imprimirRelatorioSecretaria('${s.id}', '${s.nome}')">
                                <i class="fa-solid fa-print"></i> Relatório Detalhado
                            </button>
                            <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700;">
                                ${s.total_servicos} serviços
                            </span>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <!-- Ocorrências -->
                        <div style="background: var(--bg-body); padding: 1rem; border-radius: 10px;">
                            <p style="font-weight: 600; color: var(--text-muted); font-size: 0.8rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-clipboard-list"></i> OCORRÊNCIAS</p>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem;">
                                <div><span style="color:#f59e0b;">●</span> Pendentes: <strong>${s.ocorrencias.pendentes}</strong></div>
                                <div><span style="color:#3b82f6;">●</span> Em Atend.: <strong>${s.ocorrencias.em_atendimento}</strong></div>
                                <div><span style="color:#10b981;">●</span> Resolvidas: <strong>${s.ocorrencias.resolvidas}</strong></div>
                                <div><span style="color:#64748b;">●</span> Total: <strong>${s.ocorrencias.total}</strong></div>
                            </div>
                            <div style="margin-top: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 3px;">
                                    <span>Taxa de Resolução</span>
                                    <strong style="color: ${taxaColor};">${s.ocorrencias.taxa_resolucao}%</strong>
                                </div>
                                <div style="background: #e2e8f0; border-radius: 10px; height: 8px; overflow: hidden;">
                                    <div style="background: ${taxaColor}; height: 100%; width: ${s.ocorrencias.taxa_resolucao}%; border-radius: 10px; transition: width 0.5s ease;"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Agendamentos -->
                        <div style="background: var(--bg-body); padding: 1rem; border-radius: 10px;">
                            <p style="font-weight: 600; color: var(--text-muted); font-size: 0.8rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-calendar-check"></i> AGENDAMENTOS</p>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem;">
                                <div><span style="color:#f59e0b;">●</span> Pendentes: <strong>${s.agendamentos.pendentes}</strong></div>
                                <div><span style="color:#10b981;">●</span> Confirmados: <strong>${s.agendamentos.confirmados}</strong></div>
                                <div><span style="color:#ef4444;">●</span> Cancelados: <strong>${s.agendamentos.cancelados}</strong></div>
                                <div><span style="color:#64748b;">●</span> Total: <strong>${s.agendamentos.total}</strong></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // Totais gerais
        const totalOc = data.reduce((sum, s) => sum + s.ocorrencias.total, 0);
        const totalAg = data.reduce((sum, s) => sum + s.agendamentos.total, 0);
        const totalResolvidas = data.reduce((sum, s) => sum + s.ocorrencias.resolvidas, 0);
        const taxaGeral = totalOc > 0 ? Math.round(totalResolvidas / totalOc * 100) : 0;
        
        const resumo = `
            <div class="stat-card" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, #1e293b, #334155); color: white;">
                <h4 style="color: #94a3b8; margin-bottom: 1rem;"><i class="fa-solid fa-chart-pie"></i> Resumo Geral</h4>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">
                    <div>
                        <div style="font-size: 2rem; font-weight: 800;">${totalOc}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">Ocorrências</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; font-weight: 800;">${totalAg}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">Agendamentos</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; font-weight: 800;">${totalOc + totalAg}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">Total Serviços</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; font-weight: 800; color: ${taxaGeral >= 70 ? '#10b981' : '#f59e0b'};">${taxaGeral}%</div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">Resolução</div>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = resumo + html;
    } catch(e) {
        console.error('Erro ao carregar contabilidade:', e);
    }
}

function openAdminMap(lat, lng, titulo) {
    document.getElementById('modalViewMap').style.display = 'flex';
    document.getElementById('mapModalTitle').innerText = 'Localização: ' + decodeURIComponent(titulo);
    
    const pos = [parseFloat(lat), parseFloat(lng)];

    setTimeout(() => {
        if (!adminMap) {
            adminMap = L.map('adminMapView').setView(pos, 16);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(adminMap);
            adminMarker = L.marker(pos).addTo(adminMap);
        } else {
            adminMap.setView(pos, 16);
            adminMarker.setLatLng(pos);
            adminMap.invalidateSize();
        }
    }, 300);
}

async function imprimirRelatorioSecretaria(secId, secNome) {
    const loadingBtn = event.currentTarget;
    const originalContent = loadingBtn.innerHTML;
    loadingBtn.disabled = true;
    loadingBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gerando...';

    try {
        // Fetch all data
        const [ocRes, agRes] = await Promise.all([
            fetch(`${API_URL}/ocorrencias`, { headers: { 'Authorization': `Bearer ${getToken()}` } }),
            fetch(`${API_URL}/agendamentos`, { headers: { 'Authorization': `Bearer ${getToken()}` } })
        ]);

        if (!ocRes.ok || !agRes.ok) throw new Error("Erro ao buscar dados.");

        let ocorrencias = await ocRes.json();
        let agendamentos = await agRes.json();

        // Filter for this secretaria
        ocorrencias = ocorrencias.filter(o => parseInt(o.secretaria_id) === parseInt(secId));
        agendamentos = agendamentos.filter(a => parseInt(a.secretaria_id) === parseInt(secId));

        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>Relatório Detalhado - ${secNome}</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #334155; line-height: 1.5; }
                    .header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #2563eb; padding-bottom: 20px; }
                    .header h1 { margin: 0; color: #1e3a8a; text-transform: uppercase; font-size: 1.8rem; }
                    .header p { margin: 5px 0 0; color: #64748b; font-weight: 600; }
                    
                    .section-title { background: #f1f5f9; padding: 10px 15px; border-radius: 8px; margin: 30px 0 15px; border-left: 5px solid #2563eb; font-weight: 700; color: #1e293b; display: flex; justify-content: space-between; }
                    
                    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.85rem; }
                    th { background: #f8fafc; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; color: #475569; }
                    td { padding: 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
                    
                    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
                    .badge-pending { background: #fef3c7; color: #92400e; }
                    .badge-progress { background: #dbeafe; color: #1e40af; }
                    .badge-done { background: #dcfce7; color: #166534; }
                    .badge-danger { background: #fee2e2; color: #991b1b; }
                    
                    .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
                    .summary-card { border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; text-align: center; }
                    .summary-card div:first-child { font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-bottom: 5px; }
                    .summary-card div:last-child { font-size: 1.5rem; font-weight: 800; color: #1e293b; }

                    .no-data { text-align: center; padding: 20px; color: #94a3b8; font-style: italic; }
                    
                    @media print {
                        .no-print { display: none; }
                        body { padding: 0; }
                        .summary-card { border: 1px solid #ddd; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="images/logo-prefeitura.png" alt="Logo Prefeitura" style="max-height: 150px; margin-bottom: 1rem;"><br>
                    <h1>Prefeitura de Colônia Leopoldina</h1>
                    <p>Relatório de Desempenho e Solicitações - ${secNome}</p>
                    <small>Gerado em: ${new Date().toLocaleString()}</small>
                </div>

                <div class="summary-grid">
                    <div class="summary-card">
                        <div>Total de Solicitações</div>
                        <div>${ocorrencias.length + agendamentos.length}</div>
                    </div>
                    <div class="summary-card">
                        <div>Ocorrências Resolvidas</div>
                        <div>${ocorrencias.filter(o => o.status.toLowerCase() === 'resolvido').length}</div>
                    </div>
                    <div class="summary-card">
                        <div>Agendamentos Confirmados</div>
                        <div>${agendamentos.filter(a => a.status.toLowerCase() === 'confirmado').length}</div>
                    </div>
                    <div class="summary-card">
                        <div>Taxa de Resolução</div>
                        <div>${ocorrencias.length > 0 ? Math.round(ocorrencias.filter(o => o.status.toLowerCase() === 'resolvido').length / ocorrencias.length * 100) : 0}%</div>
                    </div>
                </div>

                <div class="section-title">
                    <span>Lista de Ocorrências</span>
                    <span style="font-size: 0.8rem; font-weight: 400;">Total: ${ocorrencias.length}</span>
                </div>
                ${ocorrencias.length > 0 ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Protocolo</th>
                                <th>Data</th>
                                <th>Cidadão</th>
                                <th>Título/Assunto</th>
                                <th>Status</th>
                                <th>Localização</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ocorrencias.map(o => `
                                <tr>
                                    <td><strong>${o.protocolo || o.id}</strong></td>
                                    <td>${new Date(o.data).toLocaleDateString()}</td>
                                    <td>${o.usuario_nome || 'N/A'}</td>
                                    <td>${o.titulo}</td>
                                    <td><span class="badge badge-${o.status.toLowerCase() === 'resolvido' ? 'done' : (o.status.toLowerCase() === 'em_atendimento' ? 'progress' : 'pending')}">${o.status}</span></td>
                                    <td>${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="no-data">Nenhuma ocorrência registrada para esta secretaria.</p>'}

                <div class="section-title">
                    <span>Lista de Agendamentos</span>
                    <span style="font-size: 0.8rem; font-weight: 400;">Total: ${agendamentos.length}</span>
                </div>
                ${agendamentos.length > 0 ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Protocolo</th>
                                <th>Data/Hora</th>
                                <th>Cidadão</th>
                                <th>Assunto</th>
                                <th>Status</th>
                                <th>Senha</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${agendamentos.map(a => `
                                <tr>
                                    <td><strong>${a.protocolo || a.id}</strong></td>
                                    <td>${new Date(a.data_hora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' })} ${new Date(a.data_hora).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false })}</td>
                                    <td>${a.usuario_nome || 'N/A'}</td>
                                    <td>${a.assunto}</td>
                                    <td><span class="badge badge-${a.status.toLowerCase() === 'confirmado' ? 'done' : (a.status.toLowerCase() === 'cancelado' ? 'danger' : 'pending')}">${a.status}</span></td>
                                    <td><strong style="color: #2563eb;">${a.senha || '---'}</strong></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="no-data">Nenhum agendamento registrado para esta secretaria.</p>'}

                <div style="text-align: center; margin-top: 50px;" class="no-print">
                    <button onclick="window.print()" style="padding: 12px 40px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <i class="fa-solid fa-print"></i> Imprimir Relatório
                    </button>
                </div>
                
                <div style="margin-top: 60px; border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; font-size: 0.75rem; color: #94a3b8;">
                    Documento Oficial - Sistema Colônia Digital<br>
                    Prefeitura Municipal de Colônia Leopoldina - AL
                </div>
            </body>
            </html>
        `);
        printWindow.document.close();
    } catch (e) {
        console.error(e);
        alert("Erro ao gerar relatório: " + e.message);
    } finally {
        loadingBtn.disabled = false;
        loadingBtn.innerHTML = originalContent;
    }
}

async function imprimirContabilidadeGeral() {
    const loadingBtn = document.getElementById('btnImprimirGeral');
    if (!loadingBtn) return;
    const originalContent = loadingBtn.innerHTML;
    loadingBtn.disabled = true;
    loadingBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gerando Relatório...';

    try {
        // Fetch secretarias, ocorrencias and agendamentos
        const [secRes, ocRes, agRes] = await Promise.all([
            fetch(`${API_URL}/secretarias`, { headers: { 'Authorization': `Bearer ${getToken()}` } }),
            fetch(`${API_URL}/ocorrencias`, { headers: { 'Authorization': `Bearer ${getToken()}` } }),
            fetch(`${API_URL}/agendamentos`, { headers: { 'Authorization': `Bearer ${getToken()}` } })
        ]);

        if (!secRes.ok || !ocRes.ok || !agRes.ok) throw new Error("Erro ao buscar dados do servidor.");

        const secretarias = await secRes.json();
        const ocorrencias = await ocRes.json();
        const agendamentos = await agRes.json();

        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert("Por favor, permita popups para gerar a impressão.");
            return;
        }
        
        let secretariasHtml = '';
        
        secretarias.forEach(sec => {
            const secOcs = ocorrencias.filter(o => parseInt(o.secretaria_id) === parseInt(sec.id));
            const secAgs = agendamentos.filter(a => parseInt(a.secretaria_id) === parseInt(sec.id));
            
            if (secOcs.length === 0 && secAgs.length === 0) {
                return; // Omit empty ones for cleaner output
            }
            
            secretariasHtml += `
                <div style="page-break-inside: avoid; border-bottom: 2px dashed #cbd5e1; padding-bottom: 30px; margin-bottom: 40px;">
                    <h2 style="color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; text-transform: uppercase; font-size: 1.4rem; margin-top: 20px;">
                        ${sec.nome}
                    </h2>
                    
                    <div class="summary-grid">
                        <div class="summary-card">
                            <div>Total de Serviços</div>
                            <div>${secOcs.length + secAgs.length}</div>
                        </div>
                        <div class="summary-card">
                            <div>Ocorrências Atendidas</div>
                            <div>${secOcs.length}</div>
                        </div>
                        <div class="summary-card">
                            <div>Agendamentos Registrados</div>
                            <div>${secAgs.length}</div>
                        </div>
                        <div class="summary-card">
                            <div>Taxa de Resolução</div>
                            <div>${secOcs.length > 0 ? Math.round(secOcs.filter(o => o.status.toLowerCase() === 'resolvido').length / secOcs.length * 100) : 0}%</div>
                        </div>
                    </div>

                    <h4 style="margin: 20px 0 10px; color: #334155; font-size: 1.1rem;"><i class="fa-solid fa-clipboard-list"></i> Ocorrências Relacionadas (${secOcs.length})</h4>
                    ${secOcs.length > 0 ? `
                        <table>
                            <thead>
                                <tr>
                                    <th>Protocolo</th>
                                    <th>Data</th>
                                    <th>Cidadão</th>
                                    <th>Título/Assunto</th>
                                    <th>Status</th>
                                    <th>Localização</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${secOcs.map(o => `
                                    <tr>
                                        <td><strong>${o.protocolo || o.id}</strong></td>
                                        <td>${new Date(o.data).toLocaleDateString()}</td>
                                        <td>${o.usuario_nome || 'N/A'}</td>
                                        <td>${o.titulo}</td>
                                        <td><span class="badge badge-${o.status.toLowerCase() === 'resolvido' ? 'done' : (o.status.toLowerCase() === 'em_atendimento' ? 'progress' : 'pending')}">${o.status}</span></td>
                                        <td>${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    ` : '<p class="no-data">Nenhuma ocorrência registrada para esta secretaria.</p>'}

                    <h4 style="margin: 20px 0 10px; color: #334155; font-size: 1.1rem;"><i class="fa-solid fa-calendar-check"></i> Agendamentos e Atendimentos (${secAgs.length})</h4>
                    ${secAgs.length > 0 ? `
                        <table>
                            <thead>
                                <tr>
                                    <th>Protocolo</th>
                                    <th>Data/Hora</th>
                                    <th>Cidadão</th>
                                    <th>Assunto</th>
                                    <th>Status</th>
                                    <th>Senha/Informações</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${secAgs.map(a => `
                                    <tr>
                                        <td><strong>${a.protocolo || a.id}</strong></td>
                                        <td>${new Date(a.data_hora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' })} ${new Date(a.data_hora).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false })}</td>
                                        <td>${a.usuario_nome || 'N/A'}</td>
                                        <td>${a.assunto}</td>
                                        <td><span class="badge badge-${a.status.toLowerCase() === 'confirmado' ? 'done' : (a.status.toLowerCase() === 'cancelado' ? 'danger' : 'pending')}">${a.status}</span></td>
                                        <td>
                                            ${a.senha ? `<strong style="color: #2563eb;">Senha: ${a.senha}</strong>` : '---'}
                                            ${a.motivo ? `<br><small style="color: #64748b;">Obs: ${a.motivo}</small>` : ''}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    ` : '<p class="no-data">Nenhum agendamento registrado para esta secretaria.</p>'}
                </div>
            `;
        });

        printWindow.document.write(`
            <html>
            <head>
                <title>Relatório Contábil Geral de Atendimentos - Colônia Digital</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #334155; line-height: 1.5; }
                    .header { text-align: center; margin-bottom: 40px; border-bottom: 4px double #1e3a8a; padding-bottom: 25px; }
                    .header h1 { margin: 0; color: #1e3a8a; text-transform: uppercase; font-size: 2rem; letter-spacing: 1px; }
                    .header p { margin: 8px 0 0; color: #475569; font-weight: 700; font-size: 1.2rem; }
                    
                    .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 15px 0 25px; }
                    .summary-card { border: 1px solid #cbd5e1; padding: 12px; border-radius: 8px; text-align: center; background: #f8fafc; }
                    .summary-card div:first-child { font-size: 0.7rem; color: #64748b; text-transform: uppercase; margin-bottom: 3px; font-weight: 600; }
                    .summary-card div:last-child { font-size: 1.3rem; font-weight: 800; color: #0f172a; }
                    
                    table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 0.8rem; }
                    th { background: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; color: #334155; font-weight: 700; }
                    td { padding: 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
                    
                    .badge { padding: 3px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; display: inline-block; }
                    .badge-pending { background: #fef3c7; color: #92400e; }
                    .badge-progress { background: #dbeafe; color: #1e40af; }
                    .badge-done { background: #dcfce7; color: #166534; }
                    .badge-danger { background: #fee2e2; color: #991b1b; }
                    
                    .no-data { padding: 10px; color: #94a3b8; font-style: italic; font-size: 0.8rem; }
                    
                    @media print {
                        .no-print { display: none; }
                        body { padding: 0; }
                        .summary-card { border: 1px solid #94a3b8; background: #fff; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="images/logo-prefeitura.png" alt="Logo Prefeitura" style="max-height: 150px; margin-bottom: 1rem;"><br>
                    <h1>Prefeitura de Colônia Leopoldina</h1>
                    <p>Relatório Consolidado de Atendimentos e Serviços Municipais</p>
                    <div style="margin-top: 10px; font-size: 0.85rem; color: #64748b;">
                        <strong>Gerado por:</strong> Administrador Geral &bull; 
                        <strong>Data de Emissão:</strong> ${new Date().toLocaleString()}
                    </div>
                </div>

                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 20px; margin-bottom: 40px;">
                    <h3 style="margin-top: 0; color: #166534;"><i class="fa-solid fa-chart-pie"></i> Resumo Consolidado do Município</h3>
                    <div class="summary-grid" style="margin-bottom: 0;">
                        <div class="summary-card" style="background: white;">
                            <div>Total Geral de Atendimentos</div>
                            <div style="color: #2563eb;">${ocorrencias.length + agendamentos.length}</div>
                        </div>
                        <div class="summary-card" style="background: white;">
                            <div>Total de Ocorrências</div>
                            <div>${ocorrencias.length}</div>
                        </div>
                        <div class="summary-card" style="background: white;">
                            <div>Total de Agendamentos</div>
                            <div>${agendamentos.length}</div>
                        </div>
                        <div class="summary-card" style="background: white;">
                            <div>Taxa Geral de Resolução</div>
                            <div style="color: #166534;">${ocorrencias.length > 0 ? Math.round(ocorrencias.filter(o => o.status.toLowerCase() === 'resolvido').length / ocorrencias.length * 100) : 0}%</div>
                        </div>
                    </div>
                </div>

                ${secretariasHtml}

                <div style="text-align: center; margin-top: 50px;" class="no-print">
                    <button onclick="window.print()" style="padding: 15px 50px; background: #1e3a8a; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1.1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);">
                        <i class="fa-solid fa-print"></i> Confirmar Impressão do Relatório Geral
                    </button>
                </div>
                
                <div style="margin-top: 60px; border-top: 1px solid #cbd5e1; padding-top: 20px; text-align: center; font-size: 0.8rem; color: #64748b;">
                    Relatório Administrativo Oficial &bull; Colônia Digital &copy; 2026<br>
                    Prefeitura Municipal de Colônia Leopoldina - AL
                </div>
            </body>
            </html>
        `);
        printWindow.document.close();
    } catch (e) {
        console.error(e);
        alert("Erro ao gerar relatório geral: " + e.message);
    } finally {
        loadingBtn.disabled = false;
        loadingBtn.innerHTML = originalContent;
    }
}

window.imprimirContabilidadeGeral = imprimirContabilidadeGeral;
window.imprimirRelatorioSecretaria = imprimirRelatorioSecretaria;


async function handleConcursosUpload(e) {
    e.preventDefault();
    const concurso = document.getElementById('uploadConcursoSelect').value;
    const tipoDoc = document.getElementById('uploadTipoDoc').value;
    const fileInput = document.getElementById('uploadFileDoc');
    
    if (fileInput.files.length === 0) {
        alert("Por favor, selecione um arquivo.");
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("concurso", concurso);
    formData.append("tipo_documento", tipoDoc);
    formData.append("arquivo", file);
    
    try {
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Enviando...`;
        
        const res = await fetch(`${API_URL}/agendamentos/concursos/documentos`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: formData
        });
        
        btn.disabled = false;
        btn.innerHTML = originalText;
        
        if (res.ok) {
            alert("Documento enviado e atualizado com sucesso!");
            fileInput.value = '';
        } else {
            const err = await res.json();
            alert(`Erro no upload: ${err.detail || 'Erro desconhecido'}`);
        }
    } catch (err) {
        console.error(err);
        alert("Erro de conexão ao enviar o documento.");
    }
}

window.handleConcursosUpload = handleConcursosUpload;

async function imprimirResumoCamisas() {
    try {
        const res = await fetch(`${API_URL}/agendamentos/concurso/camisas`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        
        if (!res.ok) {
            const err = await res.json();
            alert("Erro ao buscar dados de camisas: " + (err.detail || "Erro de permissão ou conexão."));
            return;
        }
        
        const data = await res.json();
        
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert("Pop-up bloqueado. Por favor, permita pop-ups para este site para abrir a impressão.");
            return;
        }
        
        printWindow.document.write(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Consolidado de Camisas - Pé de Aço</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Outfit', 'Inter', sans-serif;
            color: #1e293b;
            margin: 0;
            padding: 2rem;
            background: #ffffff;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #a855f7;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }
        .header h1 {
            font-size: 2rem;
            color: #7c3aed;
            margin: 0;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .header p {
            font-size: 0.95rem;
            color: #64748b;
            margin: 0.5rem 0 0 0;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }
        .meta-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .meta-card h3 {
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0 0 0.5rem 0;
        }
        .meta-card .value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #7c3aed;
        }
        .tables-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2.5rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f8fafc;
            color: #475569;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
        }
        .section-title {
            font-size: 1.2rem;
            color: #1e293b;
            margin: 0 0 1rem 0;
            font-weight: 600;
            border-left: 4px solid #a855f7;
            padding-left: 0.5rem;
        }
        .summary-box {
            background: #fdf4ff;
            border: 1px solid #f3e8ff;
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .summary-box h2 {
            font-size: 1.3rem;
            color: #7c3aed;
            margin: 0 0 1rem 0;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .summary-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem 0;
            border-bottom: 1px dashed #e9d5ff;
        }
        .summary-row:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }
        .summary-row span {
            font-size: 1rem;
            font-weight: 500;
        }
        .summary-row strong {
            font-size: 1.2rem;
            color: #7c3aed;
        }
        .footer {
            margin-top: 4rem;
            text-align: center;
            font-size: 0.85rem;
            color: #94a3b8;
            border-top: 1px solid #e2e8f0;
            padding-top: 1.5rem;
        }
        .signature-section {
            margin-top: 3rem;
            display: flex;
            justify-content: space-around;
        }
        .signature-line {
            width: 250px;
            border-top: 1px solid #94a3b8;
            text-align: center;
            padding-top: 0.5rem;
            font-size: 0.9rem;
            color: #475569;
        }
        @media print {
            body {
                padding: 0;
            }
            .meta-card {
                background: none !important;
                border: 1px solid #cbd5e1 !important;
            }
            th {
                background: #f1f5f9 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .summary-box {
                background: #faf5ff !important;
                border: 1px solid #e9d5ff !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .no-print {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="images/logo-prefeitura.png" alt="Logo Prefeitura" style="max-height: 120px; margin-bottom: 1rem;">
        <img src="imagens/logo-cultura-esporte.png" alt="Logo" style="max-height: 120px; margin-bottom: 1rem; margin-left: 1rem;"><br>
        <h1>🏆 Relatório Consolidado de Camisas</h1>
        <p>CONCURSO ESPORTIVO: PÉ DE AÇO | COLÔNIA LEOPOLDINA</p>
    </div>

    <div class="meta-grid">
        <div class="meta-card">
            <h3>Total de Inscritos</h3>
            <div class="value">${data.total_inscritos}</div>
        </div>
        <div class="meta-card">
            <h3>Inscrições Ativas</h3>
            <div class="value">${data.total_ativos}</div>
        </div>
        <div class="meta-card">
            <h3>Data de Emissão</h3>
            <div class="value" style="font-size: 1.2rem; margin-top: 0.5rem;">${new Date().toLocaleDateString('pt-BR')}</div>
        </div>
    </div>

    <div class="tables-container">
        <div>
            <h3 class="section-title">Camisas dos Inscritos</h3>
            <table>
                <thead>
                    <tr>
                        <th>Tamanho</th>
                        <th style="text-align: right;">Quantidade</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>P</td>
                        <td style="text-align: right; font-weight: bold;">${data.inscritos_camisas.P}</td>
                    </tr>
                    <tr>
                        <td>M</td>
                        <td style="text-align: right; font-weight: bold;">${data.inscritos_camisas.M}</td>
                    </tr>
                    <tr>
                        <td>G</td>
                        <td style="text-align: right; font-weight: bold;">${data.inscritos_camisas.G}</td>
                    </tr>
                    <tr>
                        <td>GG</td>
                        <td style="text-align: right; font-weight: bold;">${data.inscritos_camisas.GG}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div>
            <h3 class="section-title">Camisas dos Parceiros</h3>
            <table>
                <thead>
                    <tr>
                        <th>Tamanho</th>
                        <th style="text-align: right;">Quantidade</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>P</td>
                        <td style="text-align: right; font-weight: bold;">${data.parceiros_camisas.P}</td>
                    </tr>
                    <tr>
                        <td>M</td>
                        <td style="text-align: right; font-weight: bold;">${data.parceiros_camisas.M}</td>
                    </tr>
                    <tr>
                        <td>G</td>
                        <td style="text-align: right; font-weight: bold;">${data.parceiros_camisas.G}</td>
                    </tr>
                    <tr>
                        <td>GG</td>
                        <td style="text-align: right; font-weight: bold;">${data.parceiros_camisas.GG}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="summary-box">
        <h2>👕 Total Geral Consolidado (Cidadão + Parceiro)</h2>
        <div class="summary-row">
            <span>Tamanho P</span>
            <strong>${data.inscritos_camisas.P + data.parceiros_camisas.P} unidades</strong>
        </div>
        <div class="summary-row">
            <span>Tamanho M</span>
            <strong>${data.inscritos_camisas.M + data.parceiros_camisas.M} unidades</strong>
        </div>
        <div class="summary-row">
            <span>Tamanho G</span>
            <strong>${data.inscritos_camisas.G + data.parceiros_camisas.G} unidades</strong>
        </div>
        <div class="summary-row">
            <span>Tamanho GG</span>
            <strong>${data.inscritos_camisas.GG + data.parceiros_camisas.GG} unidades</strong>
        </div>
        <div class="summary-row" style="border-top: 2px solid #7c3aed; padding-top: 1rem; margin-top: 0.5rem;">
            <span style="font-size: 1.1rem; font-weight: bold; color: #7c3aed;">TOTAL CONSOLIDADO DE CAMISAS</span>
            <strong style="font-size: 1.4rem; color: #7c3aed;">${
                data.inscritos_camisas.P + data.parceiros_camisas.P +
                data.inscritos_camisas.M + data.parceiros_camisas.M +
                data.inscritos_camisas.G + data.parceiros_camisas.G +
                data.inscritos_camisas.GG + data.parceiros_camisas.GG
            } unidades</strong>
        </div>
    </div>

    <div class="signature-section">
        <div class="signature-line">
            Secretaria de Cultura e Esporte
        </div>
        <div class="signature-line">
            Administração Geral
        </div>
    </div>

    <div class="footer">
        <p>Colônia Digital &copy; 2026 - Prefeitura de Colônia Leopoldina. Todos os direitos reservados.</p>
    </div>

    <script>
        window.onload = function() {
            setTimeout(function() {
                window.print();
            }, 300);
        };
    </script>
</body>
</html>
        `);
        printWindow.document.close();
    } catch (e) {
        console.error("Erro ao imprimir resumo:", e);
        alert("Ocorreu um erro ao gerar a impressão.");
    }
}

window.imprimirResumoCamisas = imprimirResumoCamisas;

// ==========================================
// MURAL DE AVISOS
// ==========================================
async function loadAvisosAdmin() {
    const container = document.getElementById('avisosTableContainer');
    container.innerHTML = '<p>Carregando avisos...</p>';
    try {
        const res = await fetch(`${API_URL}/avisos`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) throw new Error("Erro ao buscar avisos");
        const data = await res.json();
        
        if (data.length === 0) {
            container.innerHTML = '<div class="stat-card" style="text-align: center; color: var(--text-muted);"><p>Nenhum aviso ativo no momento.</p></div>';
            return;
        }

        let html = `
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                <thead>
                    <tr style="border-bottom: 2px solid var(--border-color); color: var(--text-muted);">
                        <th style="padding: 10px;">Data</th>
                        <th style="padding: 10px;">Tipo</th>
                        <th style="padding: 10px;">Título</th>
                        <th style="padding: 10px;">Mensagem</th>
                        <th style="padding: 10px;">Alcance (SMS)</th>
                        <th style="padding: 10px;">Ações</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach(a => {
            let badgeClass = 'bg-blue-100 text-blue-800';
            if (a.tipo === 'alerta') badgeClass = 'bg-yellow-100 text-yellow-800';
            if (a.tipo === 'urgente') badgeClass = 'bg-red-100 text-red-800';

            html += `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 10px;">${new Date(a.data_criacao).toLocaleString()}</td>
                    <td style="padding: 10px;"><span style="padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;" class="${badgeClass.split(' ')[0]} ${badgeClass.split(' ')[1]}">${a.tipo}</span></td>
                    <td style="padding: 10px; font-weight: 600;">${a.titulo}</td>
                    <td style="padding: 10px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${a.mensagem}</td>
                    <td style="padding: 10px; font-weight: bold; color: var(--success);"><i class="fa-solid fa-paper-plane"></i> ${a.destinatarios_alcancados || 0} envios</td>
                    <td style="padding: 10px;">
                        <button class="btn btn-outline" style="color: #3b82f6; border-color: #3b82f6; padding: 4px 10px; font-size: 0.8rem; margin-right: 5px;" onclick="verHistoricoAviso(${a.id})"><i class="fa-solid fa-clock-rotate-left"></i> Histórico</button>
                        <button class="btn btn-outline" style="color: #ef4444; border-color: #ef4444; padding: 4px 10px; font-size: 0.8rem;" onclick="deleteAviso(${a.id})"><i class="fa-solid fa-trash"></i> Excluir</button>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;

    } catch (e) {
        console.error(e);
        container.innerHTML = '<p style="color: red;">Erro ao carregar avisos.</p>';
    }
}

async function createAviso(e) {
    e.preventDefault();
    const titulo = document.getElementById('avisoTitulo').value;
    const tipo = document.getElementById('avisoTipo').value;
    const mensagem = document.getElementById('avisoMensagem').value;
    
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Publicando...';

    try {
        const res = await fetch(`${API_URL}/avisos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ titulo, mensagem, tipo })
        });

        if (res.ok) {
            closeModal('modalNovoAviso');
            document.getElementById('formAviso').reset();
            loadAvisosAdmin();
        } else {
            const err = await res.json();
            alert("Erro ao publicar: " + (err.detail || ""));
        }
    } catch (err) {
        console.error(err);
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function enviarMensagemAvulsa(e) {
    e.preventDefault();
    const mensagem = document.getElementById('textoMensagemAvulsa').value;
    
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enviando...';

    try {
        const res = await fetch(`${API_URL}/avisos/custom-message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ mensagem })
        });

        if (res.ok) {
            closeModal('modalMensagemAvulsa');
            document.getElementById('formMensagemAvulsa').reset();
            Swal.fire({icon: 'success', title: 'Sucesso', text: 'O disparo da mensagem foi iniciado em background!'});
            loadAvisosAdmin();
        } else {
            const err = await res.json();
            alert("Erro ao enviar: " + (err.detail || ""));
        }
    } catch (err) {
        console.error(err);
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function deleteAviso(id) {
    if(!confirm("Tem certeza que deseja remover este aviso? Ele sumirá do painel dos cidadãos.")) return;
    
    try {
        const res = await fetch(`${API_URL}/avisos/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok || res.status === 204) {
            loadAvisosAdmin();
        } else {
            alert("Erro ao deletar aviso.");
        }
    } catch (e) {
        console.error(e);
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
}


window.verDetalhesInscricao = function(id) {
    const a = window.todasInscricoes ? window.todasInscricoes.find(i => i.id == id) : null;
    if (!a) return;
    
    let html = '<div style="text-align: left; font-size: 0.9rem;">';
    html += '<p><strong>Inscrito:</strong> ' + (a.usuario_nome || 'N/A') + '</p>';
    html += '<p><strong>Protocolo:</strong> ' + (a.protocolo || a.id) + '</p>';
    html += '<p><strong>Assunto:</strong> ' + (a.assunto || 'N/A') + '</p>';
    if (a.motivo) html += '<p><strong>Motivo/Dados Extra:</strong><br>' + a.motivo.replace(/\n/g, '<br>') + '</p>';
    
    html += '<hr><p><strong>Anexos/Fotos:</strong></p>';
    if (a.anexo) {
        const files = a.anexo.split(',');
        html += '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">';
        files.forEach(f => {
            const trim = f.trim();
            if (!trim) return;
            if (trim.match(/\.(jpeg|jpg|gif|png|webp)/i)) {
                html += '<img src="' + MEDIA_URL + '/' + trim.replace(/\\/g, '/') + '" style="max-width: 100%; border-radius: 4px; border: 1px solid #ccc; max-height: 200px; cursor: pointer;" onclick="window.open(this.src, \'_blank\')">';
            } else {
                html += '<a href="' + MEDIA_URL + '/' + trim.replace(/\\/g, '/') + '" target="_blank" class="btn btn-outline"><i class="fa-solid fa-file-pdf"></i> Ver PDF</a>';
            }
        });
        html += '</div>';
    } else {
        html += '<p style="color: #ef4444; font-weight: bold;">Nenhuma foto ou documento foi anexado nesta inscrição! O usuário provavelmente se inscreveu antes da trava obrigatória de fotos.</p>';
    }
    html += '</div>';
    
    Swal.fire({
        title: 'Detalhes da Inscrição',
        html: html,
        width: 600,
        confirmButtonText: 'Fechar'
    });
};

window.imprimirDocumentacao = function(id) {
    const a = window.todasInscricoes ? window.todasInscricoes.find(i => i.id == id) : null;
    if (!a) return;
    
    if (!a.anexo) {
        Swal.fire({icon: 'warning', title: 'Sem Documentos', text: 'Esta inscrição não possui nenhuma foto ou documento anexado para impressão.'});
        return;
    }

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>Documentação - ${a.protocolo || a.id}</title>
            <style>
                body { font-family: 'Inter', sans-serif; padding: 20px; text-align: center; }
                h1 { color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
                .doc-img { max-width: 100%; margin-bottom: 30px; border: 2px solid #e2e8f0; border-radius: 8px; page-break-inside: avoid; }
                @media print { .no-print { display: none; } }
            </style>
        </head>
        <body>
            <h1>Documentação Anexada - ${a.usuario_nome}</h1>
            <p style="margin-bottom: 30px;"><strong>Protocolo:</strong> ${a.protocolo || a.id}</p>
    `);
    
    const files = a.anexo.split(',');
    let hasImages = false;
    files.forEach(f => {
        const trimFile = f.trim();
        if (!trimFile) return;
        if (trimFile.match(/\.(jpeg|jpg|gif|png|webp)/i)) {
            hasImages = true;
            let cleanPath = trimFile.replace(/\\/g, '/');
            if (cleanPath.startsWith('/')) cleanPath = cleanPath.substring(1);
            let baseMedia = MEDIA_URL;
            if (baseMedia.endsWith('/')) baseMedia = baseMedia.substring(0, baseMedia.length - 1);
            let fullUrl = `${baseMedia}/${cleanPath}`;
            printWindow.document.write(`<img class="doc-img" src="${encodeURI(fullUrl)}"><br>`);
        }
    });

    if (!hasImages) {
        printWindow.document.write('<p>Existem apenas arquivos PDF anexados. Para imprimi-los, abra os PDFs individualmente.</p>');
    }

    printWindow.document.write(`
            <div style="margin-top: 40px;" class="no-print">
                <button onclick="window.print()" style="padding: 10px 30px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1.1rem; font-weight: bold;">Imprimir</button>
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
};

async function loadPasswordResets() {
    const container = document.getElementById('passwordResetsTableContainer');
    const counter = document.getElementById('totalResetsCounter');
    
    if (!container || !counter) return;
    
    container.innerHTML = '<div style="text-align:center; padding:2rem;"><i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary)"></i></div>';

    try {
        const res = await fetch(`${API_URL}/auth/password-resets`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (!res.ok) throw new Error("Erro ao carregar recuperações de senha");

        const data = await res.json();
        
        counter.textContent = data.length;

        if (data.length === 0) {
            container.innerHTML = '<div style="background:var(--surface); border:1px solid var(--border); padding:2rem; text-align:center; border-radius:12px; color:var(--text-muted);">Nenhum histórico de solicitação encontrado.</div>';
            return;
        }

        let html = `
        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="background: var(--background); border-bottom: 2px solid var(--border);">
                            <th style="padding: 1rem; font-weight: 600; color: var(--text-muted);">Data</th>
                            <th style="padding: 1rem; font-weight: 600; color: var(--text-muted);">Usuário</th>
                            <th style="padding: 1rem; font-weight: 600; color: var(--text-muted);">Tipo</th>
                            <th style="padding: 1rem; font-weight: 600; color: var(--text-muted);">Método</th>
                            <th style="padding: 1rem; font-weight: 600; color: var(--text-muted);">Status Entrega</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.forEach(log => {
            const dateStr = new Date(log.data_solicitacao).toLocaleString('pt-BR');
            const statusBadge = log.sucesso === 1 
                ? '<span class="badge" style="background:#d1fae5; color:#065f46;"><i class="fa-solid fa-check"></i> Entregue</span>' 
                : '<span class="badge" style="background:#fee2e2; color:#991b1b;"><i class="fa-solid fa-xmark"></i> Falha</span>';
            const metodoBadge = log.metodo === 'sms' 
                ? '<span class="badge bg-blue-100 text-blue-800"><i class="fa-solid fa-mobile-screen"></i> SMS</span>' 
                : '<span class="badge" style="background:#f3f4f6; color:#374151;"><i class="fa-solid fa-envelope"></i> Email</span>';
                
            html += `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.2s;">
                    <td style="padding: 1rem; color: var(--text-secondary);">${dateStr}</td>
                    <td style="padding: 1rem; font-weight: 500; color: var(--text-primary);">${log.usuario_nome || '-'}</td>
                    <td style="padding: 1rem; color: var(--text-secondary); text-transform: capitalize;">${log.usuario_tipo}</td>
                    <td style="padding: 1rem;">${metodoBadge}</td>
                    <td style="padding: 1rem;">${statusBadge}</td>
                </tr>
            `;
        });

        html += `</tbody></table></div></div>`;
        container.innerHTML = html;

    } catch (err) {
        console.error(err);
        container.innerHTML = '<div style="background:var(--surface); border:1px solid var(--border); padding:2rem; text-align:center; border-radius:12px; color:#ef4444;">Erro ao carregar dados.</div>';
    }
}

async function verHistoricoAviso(aviso_id) {
    document.getElementById('modalAvisoHistory').style.display = 'flex';
    const tbody = document.getElementById('avisoHistoryTableBody');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 15px;"><i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary)"></i></td></tr>';

    try {
        const res = await fetch(`${API_URL}/avisos/${aviso_id}/historico`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (!res.ok) throw new Error("Erro ao carregar histórico");
        
        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 15px;">Nenhum SMS enviado para este aviso.</td></tr>';
            return;
        }

        let html = '';
        data.forEach(log => {
            const statusBadge = log.sucesso === 1 
                ? '<span style="background: #e6fffa; color: #047481; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem;"><i class="fa-solid fa-check"></i> Enviado</span>'
                : '<span style="background: #fff5f5; color: #e53e3e; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem;"><i class="fa-solid fa-xmark"></i> Falha</span>';

            const tipoFormatado = log.tipo_usuario === 'admin' ? 'Administrador' : (log.tipo_usuario === 'subadmin' ? 'Servidor' : 'Cidadão');

            html += `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 10px;">${new Date(log.data_envio).toLocaleString()}</td>
                    <td style="padding: 10px; font-weight: 500;">${log.nome_destinatario}</td>
                    <td style="padding: 10px;">${log.telefone}</td>
                    <td style="padding: 10px; color: var(--text-muted); font-size: 0.8rem;">${tipoFormatado}</td>
                    <td style="padding: 10px;">${statusBadge}</td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 15px; color: red;">Erro de conexão ao carregar histórico.</td></tr>';
    }
}

async function adminChangePassword(e) {
    e.preventDefault();
    const nova = document.getElementById("adminNovaSenha").value;
    const confirma = document.getElementById("adminConfirmaSenha").value;
    
    if (nova !== confirma) {
        Swal.fire("Erro", "As senhas no coincidem.", "error");
        return;
    }
    if (nova.length < 6) {
        Swal.fire("Erro", "A senha deve ter pelo menos 6 caracteres.", "error");
        return;
    }
    
    try {
        const res = await fetch(`${API_URL}/auth/change-password`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${getToken()}`
            },
            body: JSON.stringify({ password: nova })
        });
        
        if (res.ok) {
            Swal.fire("Sucesso", "Sua senha foi alterada com sucesso!", "success");
            document.getElementById("formAlterarSenha").reset();
        } else {
            const data = await res.json().catch(() => ({}));
            Swal.fire("Erro", data.detail || "Erro ao alterar a senha", "error");
        }
    } catch(err) {
        Swal.fire("Erro de Conexo", "No foi possvel conectar ao servidor.", "error");
    }
}


async function loadPanicoRequests() {
    loadPanicoAlerts(); // Carregar os alertas junto com as solicitacoes
    const tbody = document.getElementById("panicoRequestsBody");
    if (!tbody) return;
    tbody.innerHTML = "<tr><td colspan=\"4\" style=\"text-align: center; padding: 20px;\">Carregando...</td></tr>";

    try {
        const res = await fetch(`${API_URL}/panico/requests`, {
            headers: { "Authorization": `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const data = await res.json();
            if (data.length === 0) {
                tbody.innerHTML = "<tr><td colspan=\"4\" style=\"text-align: center; padding: 20px;\">Nenhuma solicitao pendente ou aprovada.</td></tr>";
                const totalPanicoCounter = document.getElementById("totalPanicoCounter");
                if (totalPanicoCounter) totalPanicoCounter.innerText = "0";
                return;
            }
            
            let html = "";
            let authorizedCount = 0;
            data.forEach(u => {
                const isPending = u.status === 2;
                if (!isPending) authorizedCount++;
                const statusBadge = isPending 
                    ? `<span style="background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">Pendente</span>`
                    : `<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">Autorizado</span>`;
                
                const actionBtn = isPending
                    ? `<button class="btn btn-primary" style="background: #16a34a; border-color: #16a34a; padding: 5px 10px; font-size: 0.8rem;" onclick="authorizePanicoRequest(${u.id}, true)">Aprovar</button>
                       <button class="btn btn-outline" style="color: #ef4444; border-color: #ef4444; padding: 5px 10px; font-size: 0.8rem;" onclick="authorizePanicoRequest(${u.id}, false)">Negar</button>`
                    : `<button class="btn btn-outline" style="color: #ef4444; border-color: #ef4444; padding: 5px 10px; font-size: 0.8rem;" onclick="authorizePanicoRequest(${u.id}, false)">Revogar Acesso</button>`;
                
                html += `<tr>
                    <td>${u.nome}<br><small style="color:gray;">${u.cpf || ""}</small></td>
                    <td>${u.telefone || "No informado"}</td>
                    <td>${statusBadge}</td>
                    <td style="display: flex; gap: 5px;">${actionBtn}</td>
                </tr>`;
            });
            tbody.innerHTML = html;
            const totalPanicoCounter = document.getElementById("totalPanicoCounter");
            if (totalPanicoCounter) totalPanicoCounter.innerText = authorizedCount;
        } else {
            const err = await res.json().catch(()=>({}));
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 20px; color: red;">${err.detail || "Erro ao carregar"}</td></tr>`;
        }
    } catch (e) {
        console.error(e);
        tbody.innerHTML = "<tr><td colspan=\"4\" style=\"text-align: center; padding: 20px; color: red;\">Erro de conexo</td></tr>";
    }
}

async function loadPanicoAlerts() {
    const tbody = document.getElementById("panicoAlertsBody");
    if (!tbody) return;
    tbody.innerHTML = "<tr><td colspan=\"4\" style=\"text-align: center; padding: 20px;\">Carregando...</td></tr>";

    try {
        const res = await fetch(`${API_URL}/panico/alerts`, {
            headers: { "Authorization": `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const data = await res.json();
            if (data.length === 0) {
                tbody.innerHTML = "<tr><td colspan=\"4\" style=\"text-align: center; padding: 20px;\">Nenhum alerta registrado.</td></tr>";
                return;
            }
            
            let html = "";
            data.forEach(a => {
                const dateStr = a.data_hora ? new Date(a.data_hora).toLocaleString('pt-BR') : 'Desconhecido';
                html += `<tr>
                    <td><strong>${a.nome}</strong><br><small style="color:gray;">Tel: ${a.telefone || "Não informado"}</small></td>
                    <td><span style="color: #ef4444; font-weight: bold;">${dateStr}</span></td>
                    <td>${a.endereco || "Não informado"}</td>
                    <td>${a.ponto_referencia || "Não informado"}</td>
                </tr>`;
            });
            tbody.innerHTML = html;
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 15px; color: red;">Erro ao carregar alertas.</td></tr>';
        }
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 15px; color: red;">Erro de conexão.</td></tr>';
    }
}

window.imprimirRelatorioPanico = async function() {
    try {
        const res = await fetch(`${API_URL}/panico/alerts`, {
            headers: { "Authorization": `Bearer ${getToken()}` }
        });
        if (!res.ok) {
            alert("Erro ao buscar dados do botão do pânico.");
            return;
        }
        
        const data = await res.json();
        
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert("Por favor, permita popups para gerar a impressão.");
            return;
        }

        let tableHtml = "";
        if (data.length === 0) {
            tableHtml = "<p class='no-data'>Nenhum alerta de socorro registrado no histórico.</p>";
        } else {
            tableHtml = `
                <table>
                    <thead>
                        <tr>
                            <th>Cidadão / Contato</th>
                            <th>Data e Hora</th>
                            <th>Endereço</th>
                            <th>Ponto de Referência</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(a => {
                            const dateStr = a.data_hora ? new Date(a.data_hora).toLocaleString('pt-BR') : 'Desconhecido';
                            return `<tr>
                                <td><strong>${a.nome}</strong><br><small style="color: #64748b;">Tel: ${a.telefone || "Não informado"}</small></td>
                                <td><span style="color: #ef4444; font-weight: bold;">${dateStr}</span></td>
                                <td>${a.endereco || "Não informado"}</td>
                                <td>${a.ponto_referencia || "Não informado"}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>
            `;
        }

        printWindow.document.write(`
            <html>
            <head>
                <title>Relatório - Botão do Pânico</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #334155; line-height: 1.5; }
                    .header { text-align: center; margin-bottom: 40px; border-bottom: 4px double #ef4444; padding-bottom: 25px; }
                    .header h1 { margin: 0; color: #ef4444; text-transform: uppercase; font-size: 2rem; letter-spacing: 1px; }
                    .header p { margin: 8px 0 0; color: #475569; font-weight: 700; font-size: 1.2rem; }
                    
                    table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 0.9rem; }
                    th { background: #fef2f2; text-align: left; padding: 12px; border-bottom: 2px solid #fca5a5; color: #991b1b; font-weight: 700; }
                    td { padding: 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
                    
                    .no-data { padding: 10px; color: #94a3b8; font-style: italic; font-size: 0.9rem; text-align: center; }
                    
                    @media print {
                        .no-print { display: none; }
                        body { padding: 0; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="images/logo-prefeitura.png" alt="Logo Prefeitura" style="max-height: 150px; margin-bottom: 1rem;"><br>
                    <h1>Histórico de Alertas de Socorro</h1>
                    <p>Relatório Geral do Botão do Pânico</p>
                    <div style="margin-top: 10px; font-size: 0.85rem; color: #64748b;">
                        <strong>Gerado por:</strong> Administrador Geral &bull; 
                        <strong>Data de Emissão:</strong> ${new Date().toLocaleString('pt-BR')}
                    </div>
                </div>

                ${tableHtml}

                <div style="text-align: center; margin-top: 40px;">
                    <button onclick="window.print()" class="no-print" style="padding: 10px 30px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer;">Imprimir</button>
                </div>
            </body>
            </html>
        `);
        printWindow.document.close();

    } catch (e) {
        console.error(e);
        alert("Erro ao gerar relatório do botão do pânico.");
    }
};

async function authorizePanicoRequest(userId, authorize) {
    if (!confirm(authorize ? "Tem certeza que deseja AUTORIZAR este cidado?" : "Tem certeza que deseja NEGAR/REVOGAR o acesso deste cidado?")) return;
    
    try {
        const res = await fetch(`${API_URL}/panico/authorize`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` },
            body: JSON.stringify({ user_id: userId, authorize: authorize })
        });
        
        if (res.ok) {
            Swal.fire("Sucesso", "Status atualizado.", "success");
            loadPanicoRequests();
        } else {
            const err = await res.json().catch(()=>({}));
            Swal.fire("Erro", err.detail || "No foi possvel atualizar o status.", "error");
        }
    } catch (e) {
        console.error(e);
        Swal.fire("Erro", "Falha de conexo com o servidor.", "error");
    }
}

async function addPanicoUser() {
    const nome = document.getElementById('addPanicoNome').value.trim();
    const cpf = document.getElementById('addPanicoCPF').value.trim();
    const telefone = document.getElementById('addPanicoTelefone').value.trim();
    const endereco = document.getElementById('addPanicoEndereco').value.trim();
    
    if (!nome || !cpf || !telefone || !endereco) {
        Swal.fire("Erro", "Preencha todos os campos do cidadão.", "error");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/panico/add_user`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` },
            body: JSON.stringify({ 
                nome: nome,
                cpf: cpf,
                telefone: telefone,
                endereco: endereco
            })
        });
        
        if (res.ok) {
            Swal.fire("Sucesso", "Cidadão adicionado ao Botão de Pânico com sucesso!", "success");
            document.getElementById('addPanicoNome').value = '';
            document.getElementById('addPanicoCPF').value = '';
            document.getElementById('addPanicoTelefone').value = '';
            document.getElementById('addPanicoEndereco').value = '';
            loadPanicoRequests();
        } else {
            const err = await res.json().catch(()=>({}));
            Swal.fire("Erro", err.detail || "Não foi possível cadastrar o usuário.", "error");
        }
    } catch (e) {
        console.error(e);
        Swal.fire("Erro", "Falha de conexão com o servidor.", "error");
    }
}

async function changeSubAdminPhone(adminId, currentPhone) {
    const { value: novoTelefone } = await Swal.fire({
        title: 'Trocar Telefone',
        input: 'text',
        inputLabel: 'Novo Telefone',
        inputValue: currentPhone || '',
        showCancelButton: true,
        confirmButtonText: 'Salvar',
        cancelButtonText: 'Cancelar',
        inputValidator: (value) => {
            if (!value) {
                return 'Você precisa digitar um telefone!';
            }
        }
    });

    if (novoTelefone) {
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${API_URL}/admin-users/secretaria-admins/${adminId}/telefone`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ novo_telefone: novoTelefone })
            });

            if (res.ok) {
                Swal.fire('Sucesso!', 'Telefone atualizado com sucesso.', 'success');
                if (document.getElementById('admins').classList.contains('active')) loadAdmins();
                if (document.getElementById('usuarios-todos').classList.contains('active')) loadAllUsersCombined();
            } else {
                const err = await res.json();
                Swal.fire('Erro', err.detail || 'Não foi possível atualizar o telefone.', 'error');
            }
        } catch (e) {
            Swal.fire('Erro', 'Falha de conexão com o servidor.', 'error');
        }
    }
}


function imprimirFichaPolicial(id) {
    // Collect all data from the form to print
    const dataFato = document.getElementById('fp_data_fato')?.value || '';
    const horaFato = document.getElementById('fp_hora_fato')?.value || '';
    const horaRegistro = document.getElementById('fp_hora_registro')?.value || '';
    const tipo = document.querySelector('input[name="fp_tipo_ocorrencia"]:checked')?.value || document.getElementById('fp_tipo_ocorrencia_outro')?.value || '';
    
    const vitimaNome = document.getElementById('fp_vitima_nome')?.value || '';
    const vitimaCPF = document.getElementById('fp_vitima_cpf_rg')?.value || '';
    const vitimaData = document.getElementById('fp_vitima_data_nascimento')?.value || '';
    const vitimaEnd = document.getElementById('fp_vitima_endereco')?.value || '';
    const vitimaTel = document.getElementById('fp_vitima_telefone')?.value || '';
    
    const suspeitoNome = document.getElementById('fp_suspeito_nome')?.value || '';
    const suspeitoApelido = document.getElementById('fp_suspeito_apelido')?.value || '';
    const suspeitoCPF = document.getElementById('fp_suspeito_cpf_rg')?.value || '';
    const suspeitoData = document.getElementById('fp_suspeito_data_nascimento')?.value || '';
    const suspeitoEnd = document.getElementById('fp_suspeito_endereco')?.value || '';
    const suspeitoCarac = document.getElementById('fp_suspeito_caracteristicas')?.value || '';
    
    const objetos = document.getElementById('fp_objetos_envolvidos')?.value || '';
    const desc = document.getElementById('fp_descricao_detalhada')?.value || '';
    
    const algemas = document.getElementById('fp_uso_algemas')?.value || '';
    const algemasJust = document.getElementById('fp_uso_algemas_justificativa')?.value || '';
    const forca = document.getElementById('fp_emprego_forca')?.value || '';
    const forcaTipo = document.getElementById('fp_emprego_forca_tipo')?.value || '';
    const forcaJust = document.getElementById('fp_emprego_forca_justificativa')?.value || '';
    
    const providencias = document.getElementById('fp_providencias_gcm')?.value || '';
    const agentes = document.getElementById('fp_agentes_envolvidos')?.value || '';
    const viatura = document.getElementById('fp_viatura')?.value || '';
    const encaminhamento = document.getElementById('fp_encaminhamento')?.value || '';
    
    const resp = document.getElementById('fp_agente_responsavel')?.value || '';
    const cmd = document.getElementById('fp_comandante_geral')?.value || '';

    const win = window.open('', '_blank');
    win.document.write(`
        <html>
        <head>
            <title>Ficha de Ocorrência Policial #${id}</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; line-height: 1.4; color: #000; }
                h2 { text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }
                .section { margin-bottom: 20px; border: 1px solid #ccc; padding: 10px; }
                .section-title { font-weight: bold; background: #eee; padding: 5px; margin: -10px -10px 10px -10px; border-bottom: 1px solid #ccc; }
                .row { display: flex; margin-bottom: 5px; }
                .col { flex: 1; padding: 0 5px; }
                .label { font-weight: bold; font-size: 0.85em; color: #555; }
                .val { border-bottom: 1px solid #000; min-height: 1.2em; display: inline-block; width: 100%; font-family: monospace; font-size: 1.1em;}
                @media print {
                    body { -webkit-print-color-adjust: exact; }
                }
            </style>
        </head>
        <body>
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="${window.location.origin}/images/logo-gcm.png" alt="Logo GCM" style="max-height: 120px;" onerror="this.style.display='none'">
            </div>
            <h2>Ficha de Ocorrência Policial (GCM) - Protocolo #${id}</h2>
            
            <div class="section">
                <div class="section-title">1. IDENTIFICAÇÃO DA OCORRÊNCIA</div>
                <div class="row">
                    <div class="col"><div class="label">Data do Fato:</div><div class="val">${dataFato}</div></div>
                    <div class="col"><div class="label">Hora do Fato:</div><div class="val">${horaFato}</div></div>
                    <div class="col"><div class="label">Hora do Registro:</div><div class="val">${horaRegistro}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">2. TIPO DE OCORRÊNCIA</div>
                <div class="row">
                    <div class="col"><div class="val">${tipo}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">3. DADOS DA VÍTIMA</div>
                <div class="row">
                    <div class="col" style="flex:2"><div class="label">Nome:</div><div class="val">${vitimaNome}</div></div>
                    <div class="col"><div class="label">CPF/RG:</div><div class="val">${vitimaCPF}</div></div>
                    <div class="col"><div class="label">Data Nasc.:</div><div class="val">${vitimaData}</div></div>
                </div>
                <div class="row">
                    <div class="col" style="flex:2"><div class="label">Endereço:</div><div class="val">${vitimaEnd}</div></div>
                    <div class="col"><div class="label">Telefone:</div><div class="val">${vitimaTel}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">4. DADOS DO ENVOLVIDO/SUSPEITO</div>
                <div class="row">
                    <div class="col"><div class="label">Nome:</div><div class="val">${suspeitoNome}</div></div>
                    <div class="col"><div class="label">Apelido:</div><div class="val">${suspeitoApelido}</div></div>
                    <div class="col"><div class="label">CPF/RG:</div><div class="val">${suspeitoCPF}</div></div>
                </div>
                <div class="row">
                    <div class="col"><div class="label">Data Nasc.:</div><div class="val">${suspeitoData}</div></div>
                    <div class="col" style="flex:2"><div class="label">Endereço:</div><div class="val">${suspeitoEnd}</div></div>
                </div>
                <div class="row">
                    <div class="col"><div class="label">Características:</div><div class="val" style="min-height: 40px; white-space: pre-wrap;">${suspeitoCarac}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">5. OBJETOS / BENS ENVOLVIDOS</div>
                <div class="row">
                    <div class="col"><div class="val" style="min-height: 40px; white-space: pre-wrap;">${objetos}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">7. DESCRIÇÃO DETALHADA</div>
                <div class="row">
                    <div class="col"><div class="val" style="min-height: 80px; white-space: pre-wrap;">${desc}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">8. USO DE ALGEMAS / 9. EMPREGO DA FORÇA</div>
                <div class="row">
                    <div class="col"><div class="label">Uso de Algemas:</div><div class="val">${algemas}</div></div>
                    <div class="col" style="flex:2"><div class="label">Justificativa (SV 11 STF):</div><div class="val">${algemasJust}</div></div>
                </div>
                <div class="row" style="margin-top: 10px;">
                    <div class="col"><div class="label">Emprego da Força:</div><div class="val">${forca}</div></div>
                    <div class="col"><div class="label">Tipo:</div><div class="val">${forcaTipo}</div></div>
                    <div class="col" style="flex:2"><div class="label">Justificativa:</div><div class="val">${forcaJust}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">10. PROVIDÊNCIAS ADOTADAS PELA GCM</div>
                <div class="row">
                    <div class="col"><div class="val" style="min-height: 40px; white-space: pre-wrap;">${providencias}</div></div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">11. AGENTES ENVOLVIDOS / 12. ENCAMINHAMENTO</div>
                <div class="row">
                    <div class="col" style="flex:2"><div class="label">Agentes:</div><div class="val" style="min-height: 40px; white-space: pre-wrap;">${agentes}</div></div>
                    <div class="col"><div class="label">Viatura:</div><div class="val">${viatura}</div></div>
                </div>
                <div class="row" style="margin-top: 10px;">
                    <div class="col"><div class="label">Encaminhamento:</div><div class="val">${encaminhamento}</div></div>
                </div>
            </div>

            <div style="margin-top: 50px; display: flex; justify-content: space-around; text-align: center;">
                <div style="width: 40%;">
                    <div style="border-top: 1px solid #000; padding-top: 5px; font-weight: bold;">${resp || 'Assinatura do Agente Responsável'}</div>
                </div>
                <div style="width: 40%;">
                    <div style="border-top: 1px solid #000; padding-top: 5px; font-weight: bold;">${cmd || 'Assinatura do Comandante Geral'}</div>
                </div>
            </div>

        </body>
        </html>
    `);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 500);
}
