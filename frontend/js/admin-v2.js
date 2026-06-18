// admin-v2.js - Administrative Dashboard Logic v2.0
const ADMIN_API = `${API_URL}/admin`;

let currentRole = "";
let currentSecId = null;
let statusChart = null;
let adminMap, adminMarker;

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
        <div class="nav-item" onclick="showSection('concursos', this)">
            <i class="fa-solid fa-trophy"></i><span>Concursos</span>
        </div>
    `;

    if (currentRole === 'admin') {
        html += `
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
    const restricted = ['usuarios', 'auditoria', 'usuarios-todos', 'contabilidade', 'avisos'];
    if (restricted.includes(sectionId) && currentRole !== 'admin') {

        alert("Acesso restrito ao Administrador Geral.");
        return;
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
        'config': 'Minha Conta',
        'avisos': 'Mural de Avisos'
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
    if (sectionId === 'avisos') loadAvisosAdmin();
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

    grid.innerHTML = html;
}

function renderDashboardChart(oc) {
    const ctx = document.getElementById('statusChartAdmin').getContext('2d');
    if (statusChart) statusChart.destroy();
    
    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pendentes', 'Resolvidas'],
            datasets: [{
                data: [oc.pendentes, oc.resolvidas],
                backgroundColor: ['#f59e0b', '#10b981'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            cutout: '70%',
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

async function loadRecentActivity() {
    try {
        const res = await fetch(`${API_URL}/ocorrencias`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            let list = await res.json();
            // Filter by sec if subadmin
            if (currentSecId) list = list.filter(o => parseInt(o.secretaria_id) === parseInt(currentSecId));
            
            const container = document.getElementById('recentActivity');
            container.innerHTML = '';
            
            list.slice(0, 5).forEach(o => {
                const s = o.status.toLowerCase();
                const statusType = s === 'resolvido' ? 'done' : (s === 'em_atendimento' ? 'progress' : 'pending');
                container.innerHTML += `
                    <div style="padding: 1rem 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600; font-size: 0.9rem;">${o.titulo}</div>
                            <div style="font-size: 0.8rem; color: var(--text-muted);">#${o.protocolo || o.id} • ${new Date(o.data).toLocaleDateString()}${o.usuario_nome ? ' • Cidadão: ' + o.usuario_nome : ''}</div>
                            ${o.latitude != null && o.longitude != null ? `<a href="javascript:void(0)" onclick="openAdminMap('${o.latitude}', '${o.longitude}', '${encodeURIComponent(o.titulo)}')" style="color: #10b981; font-weight: 600; text-decoration: none; font-size: 0.75rem; display: inline-block; margin-top: 2px;"><i class="fa-solid fa-location-dot"></i> Ver no Mapa</a>` : ''}
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span class="badge badge-${statusType}">${o.status}</span>
                            ${o.latitude && o.longitude ? `<button class="btn btn-outline" title="Ver no Mapa" style="border-color: #10b981; color: #10b981; padding: 4px 10px; font-size: 0.75rem;" onclick="openAdminMap('${o.latitude}', '${o.longitude}', '${encodeURIComponent(o.titulo)}')"><i class="fa-solid fa-location-dot"></i></button>` : ''}
                            ${currentRole==='admin' && s !== 'resolvido' ? `<button class="btn" style="background-color: #ef4444; color: white; border: none; font-weight: bold; margin-left: 8px; padding: 4px 10px; border-radius: 6px; box-shadow: 0 2px 5px rgba(239, 68, 68, 0.4); display: flex; align-items: center; gap: 5px; font-size: 0.75rem;" title="Cobrar Secretaria URGENTE" onclick="cobrarSecretaria('${o.id}')"><i class="fa-solid fa-bell fa-shake"></i> Cobrar</button>` : ''}
                        </div>
                    </div>
                `;
            });
        }
    } catch(e) { console.error(e); }
}

async function loadOcorrencias() {
    const status = document.getElementById('filterOcorrenciaStatus').value;
    const url = `${API_URL}/ocorrencias${status ? '?status='+status : ''}`;
    
    try {
        const res = await fetch(url, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            let list = await res.json();
            if (currentSecId) list = list.filter(o => parseInt(o.secretaria_id) === parseInt(currentSecId));
            
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
                const statusBtn = s === 'resolvido' ? 
                    `<button class="btn btn-outline" onclick="imprimirProtocolo('${o.id}')"><i class="fa-solid fa-print"></i></button>` :
                    `<button class="btn btn-primary" onclick="openResponseModal('${o.id}', '${o.titulo}')">Atualizar</button>`;

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

function openResponseModal(id, title) {
    document.getElementById('modalResponseTitle').innerText = `Atualizar #${id}`;
    document.getElementById('modalResponseSubtitle').innerText = title;
    document.getElementById('respText').value = "";
    document.getElementById('modalResponse').style.display = 'flex';
    
    document.getElementById('btnConfirmResp').onclick = () => confirmResolution(id);
}

async function confirmResolution(id) {
    const resp = document.getElementById('respText').value;
    if (!resp) return alert("Por favor, digite uma resposta para o cidadão.");
    
    const formData = new FormData();
    formData.append('resposta', resp);
    
    const fotoInput = document.getElementById('respFoto');
    if (fotoInput && fotoInput.files.length > 0) {
        formData.append('foto_resolucao', fotoInput.files[0]);
    }
    const selStatus = document.getElementById('respStatus') ? document.getElementById('respStatus').value : 'resolvido';
    
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=${selStatus}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        if (res.ok) {
            closeModal('modalResponse');
            if (document.getElementById('respFoto')) document.getElementById('respFoto').value = "";
            loadOcorrencias();
            loadDashboard();
            alert("Resposta enviada com sucesso!");
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Erro ao resolver: " + (err.detail || res.statusText));
        }
    } catch(e) { alert("Erro de conexão: " + e.message); }
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
                        <h1>📌 CERTIFICADO DE CONCLUSÃO</h1>
                        <p>PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA -AL</p>
                    </div>
                    <div class="content">
                        <div class="row"><span class="label">PROTOCOLO:</span> <strong>${o.protocolo}</strong></div>
                        <div class="row"><span class="label">CIDADÃO:</span> ${o.usuario_nome || 'N/A'}</div>
                        <div class="row"><span class="label">ASSUNTO:</span> ${o.titulo}</div>
                        <div class="row"><span class="label">LOCAL:</span> ${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}</div>
                        <div class="row"><span class="label">DATA:</span> ${new Date(o.data).toLocaleString()}</div>
                        <div class="row"><span class="label">SITUAÇÃO:</span> RESOLVIDO</div>
                        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                        <div>
                            <span class="label">RESPOSTA ADM:</span>
                            <p>${(o.respostas && o.respostas.length > 0) ? o.respostas[o.respostas.length-1].mensagem : 'Serviço concluído com sucesso.'}</p>
                            ${o.foto_resolucao ? `
                                <div style="margin-top: 15px; text-align: center;">
                                    <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 5px;">FOTO DA SOLUÇÃO:</p>
                                    <img src="${MEDIA_URL}/${o.foto_resolucao}" style="max-width: 100%; border-radius: 8px; border: 1px solid #e2e8f0;">
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="stamp"><div class="badge">SERVIÇO FINALIZADO</div></div>
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
                        body { font-family: 'Inter', sans-serif; padding: 40px; line-height: 1.6; color: #1e293b; }
                        .header { text-align: center; margin-bottom: 40px; border-bottom: 4px solid #10b981; padding-bottom: 20px; }
                        .content { background: #f8fafc; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; }
                        .row { display: flex; margin-bottom: 15px; }
                        .label { width: 140px; font-weight: 700; color: #64748b; }
                        .stamp { margin-top: 40px; text-align: right; }
                        .badge { padding: 10px 20px; border: 2px solid ${stampColor}; color: ${stampColor}; font-weight: 800; border-radius: 8px; display: inline-block; transform: rotate(-5deg); }
                        @media print { .no-print { display: none; } }
                    </style>
                </head>
                <body>
                    <div class="header">
                        ${isCulturaEsporte ? `<img src="imagens/logo-cultura-esporte.png" alt="Logo" style="max-height: 120px; margin-bottom: 1rem;"><br>` : ''}
                        <h1>${iconHeader} ${titleText}</h1>
                        <p>PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA -AL</p>
                    </div>
                    <div class="content">
                        <div class="row"><span class="label">PROTOCOLO:</span> <strong>${a.protocolo || a.id}</strong></div>
                        ${a.senha ? `<div class="row"><span class="label" style="color: #2563eb;">${isConcurso ? 'Nº DE INSCRIÇÃO:' : 'SENHA:'}</span> <strong style="font-size: 1.2rem; color: #2563eb;">${a.senha}</strong></div>` : ''}
                        <div class="row"><span class="label">CIDADÃO:</span> <strong>${a.usuario_nome || 'N/A'}${isConcurso && parceiroNome ? ` e ${parceiroNome}` : ''}</strong></div>
                        <div class="row"><span class="label">ENDEREÇO:</span> ${a.usuario_endereco || 'Não informado'}</div>
                        ${parceiroNome ? `<div class="row"><span class="label">PARCEIRO(A):</span> <strong>${parceiroNome}</strong></div>` : ''}
                        <div class="row"><span class="label">ASSUNTO:</span> ${a.assunto}</div>
                        ${a.motivo ? `<div class="row" style="white-space: pre-line;"><span class="label">MOTIVO:</span> ${a.motivo}</div>` : ''}
                        ${a.cartao_sus ? `<div class="row"><span class="label">CARTÃO SUS:</span> ${a.cartao_sus}</div>` : ''}
                        ${a.acompanhante ? `<div class="row"><span class="label">ACOMPANHANTE:</span> ${a.acompanhante}</div>` : ''}
                        <div class="row" style="background: #f1f5f9; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;"><span class="label">${dateLabel}</span> <strong style="font-size: 1.2rem; color: #1e293b;">${(() => { const d = new Date(a.data_hora); const od = { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' }; const ot = { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false }; return d.toLocaleDateString('pt-BR', od) + ' às ' + d.toLocaleTimeString('pt-BR', ot) + ' (Horário de Brasília)'; })()}</strong></div>
                        <div class="row"><span class="label">SITUAÇÃO:</span> <strong style="color: ${statusColor};">${statusText}</strong></div>
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

            let html = `<table class="data-table"><thead><tr><th>Nome</th><th>Secretaria</th><th>E-mail</th><th>Telefone</th><th>Ações</th></tr></thead><tbody>`;
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
                        <button class="btn" style="background-color: #f59e0b; color: white; border: none; font-size: 0.7rem; padding: 4px 10px; border-radius: 6px; display: flex; align-items: center; gap: 4px;" title="Notificar Pendências" onclick="notificarSubAdmin('${a.id}', '${a.nome}')"><i class="fa-solid fa-bell"></i> Notificar</button>
                        <button class="btn btn-outline" style="color: var(--danger); font-size: 0.7rem; padding: 4px 10px;" onclick="deleteAdmin('${a.id}')"><i class="fa-solid fa-trash"></i></button>
                    `;
                }

                html += `
                    <tr>
                        <td>${a.nome}</td>
                        <td><span class="badge badge-progress">${sMap[a.secretaria_id] || 'N/A'}</span></td>
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
    const data = {
        nome: document.getElementById('newAdminName').value,
        cpf: document.getElementById('newAdminCPF').value,
        email: document.getElementById('newAdminEmail').value,
        telefone: document.getElementById('newAdminTel').value,
        senha: document.getElementById('newAdminPass').value,
        secretaria_id: parseInt(document.getElementById('newAdminSec').value)
    };
    try {
        const res = await fetch(`${ADMIN_API}/users/secretaria-admins`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify(data)
        });
        if (res.ok) {
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
            
            let html = `<table class="data-table"><thead><tr><th>Nome</th><th>E-mail</th><th>Tipo</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(u => {
                const color = u.tipo === 'admin' ? '#ef4444' : (u.tipo === 'subadmin' ? '#f59e0b' : '#22c55e');
                        const s = u.status.toLowerCase();
                        html += `
                    <tr>
                        <td><strong>${u.nome}</strong></td>
                        <td>${u.email}</td>
                        <td><span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; background: ${color}20; color: ${color}; font-weight: 600;">${u.tipo.toUpperCase()}</span></td>
                        <td><span class="badge badge-${s === 'ativo' ? 'done' : 'pending'}">${u.status}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                <button class="btn btn-primary" style="font-size: 0.7rem; padding: 4px 10px;" onclick="openPasswordModal('${u.id}', '${u.source}', '${u.nome}')"><i class="fa-solid fa-key"></i> Trocar Senha</button>
                                <button class="btn btn-outline" style="color: var(--danger); font-size: 0.7rem; padding: 4px 10px;" onclick="deleteCombinedUser('${u.id}', '${u.source}')"><i class="fa-solid fa-trash"></i></button>
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

async function deleteCombinedUser(id, source) {
    if (!confirm("Excluir permanentemente este usuário?")) return;
    const url = source === 'subadmin' ? `${ADMIN_API}/users/secretaria-admins/${id}` : `${ADMIN_API}/users/${id}`;
    try {
        const res = await fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) { loadAllCombinedUsers(); loadDashboard(); }
    } catch(e) { Swal.fire({icon: 'error', title: 'Erro', text: 'Erro ao excluir.'}); }
}

function openPasswordModal(id, source, nome) {
    if (!id || id === 'undefined' || id === 'null') {
        alert("Erro crítico: ID do usuário está vazio ou indefinido ao abrir o modal!");
        return;
    }
    document.getElementById('senha_user_id').value = id;
    document.getElementById('senha_user_source').value = source;
    document.getElementById('modalSenhaTitle').innerText = `Alterar Senha: ${nome}`;
    document.getElementById('nova_senha_input').value = '';
    document.getElementById('modalAlterarSenha').style.display = 'block';
}

document.getElementById('formAlterarSenha').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('senha_user_id').value;
    const source = document.getElementById('senha_user_source').value;
    const new_password = document.getElementById('nova_senha_input').value;

    if (!new_password) return alert("Digite a nova senha.");

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
            alert("Senha alterada com sucesso!");
            document.getElementById('modalAlterarSenha').style.display = 'none';
        } else {
            const err = await res.json();
            const errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail || "Erro desconhecido.");
            alert("Erro ao alterar senha: " + errorMsg);
        }
    } catch(e) {
        Swal.fire({icon: 'error', title: 'Erro', text: 'Erro de conexão.'});
    }
});

// Admin self-password update (from config section)
async function updatePassword(e) {
    if (e) e.preventDefault();
    const current = document.getElementById('pwCurrent').value;
    const newPw = document.getElementById('pwNew').value;
    const confirm = document.getElementById('pwConfirm').value;

    if (!current || !newPw || !confirm) {
        alert("Por favor, preencha todos os campos de senha.");
        return;
    }
    if (newPw !== confirm) {
        alert("A nova senha e a confirmação não coincidem.");
        return;
    }
    if (newPw.length < 6) {
        alert("A nova senha deve ter pelo menos 6 caracteres.");
        return;
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
            alert("Senha alterada com sucesso!");
            document.getElementById('pwCurrent').value = '';
            document.getElementById('pwNew').value = '';
            document.getElementById('pwConfirm').value = '';
        } else {
            const err = await res.json().catch(() => ({}));
            const errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail || "Erro desconhecido.");
            alert("Erro: " + errorMsg);
        }
    } catch(e) {
        alert("Erro de conexão: " + e.message);
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
        <img src="imagens/logo-cultura-esporte.png" alt="Logo" style="max-height: 120px; margin-bottom: 1rem;"><br>
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
                    <td style="padding: 10px;">
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

