// admin-v2.js - Administrative Dashboard Logic v2.0
const ADMIN_API = `${API_URL}/admin`;

let currentRole = "";
let currentSecId = null;
let statusChart = null;

document.addEventListener('DOMContentLoaded', () => {
    if (!checkAuth(true)) {
        // Sem autenticação ou permissão de admin — redirecionar para login do painel
        window.location.href = 'admin/index.html';
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
    const user = getUserInfo();
    currentRole = user.tipo_usuario;

    currentSecId = user.secretaria_id;
    
    // Update User Info in header
    document.getElementById('userName').innerText = user.nome || user.email;
    document.getElementById('userRole').innerText = currentRole === 'admin' ? 'Administrador Geral' : `Sub-Administrador (${user.secretaria_nome || 'Secretaria'})`;
    document.getElementById('roleDebug').innerText = `[${currentRole}]`;
    
    // Avatar Logic
    const avatar = document.getElementById('userAvatar');
    if (user.foto_perfil) {
        avatar.innerHTML = `<img src="${MEDIA_URL}${user.foto_perfil}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
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
            <div class="nav-item" onclick="showSection('usuarios', this)">
                <i class="fa-solid fa-users"></i><span>Gestão de Cidadãos</span>
            </div>
            <div class="nav-item" onclick="showSection('admins', this)">
                <i class="fa-solid fa-user-shield"></i><span>Gerenciar Sub-Admins</span>
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
    const restricted = ['usuarios', 'admins', 'auditoria', 'usuarios-todos', 'contabilidade'];
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
        'usuarios': 'Gestão de Cidadãos',
        'admins': 'Sub-Administradores',
        'auditoria': 'Logs de Auditoria',
        'usuarios-todos': 'Gestão de Todos os Usuários',
        'contabilidade': 'Contabilidade por Secretaria',
        'config': 'Minha Conta'
    };
    document.getElementById('pageTitle').innerText = titles[sectionId];
    document.getElementById('breadcrumb').innerText = `Início / ${titles[sectionId]}`;

    // Load data specific to section
    if (sectionId === 'dashboard') loadDashboard();
    if (sectionId === 'ocorrencias') loadOcorrencias();
    if (sectionId === 'agendamentos') loadAgendamentos();
    if (sectionId === 'usuarios') loadUsers();
    if (sectionId === 'admins') loadAdmins();
    if (sectionId === 'auditoria') loadAuditLogs();
    if (sectionId === 'usuarios-todos') loadAllCombinedUsers();
    if (sectionId === 'contabilidade') loadPerformance();
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
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span class="badge badge-${statusType}">${o.status}</span>
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
                    `<button class="btn btn-primary" onclick="openResponseModal('${o.id}', '${o.titulo}')">Resolver</button>`;

                html += `
                    <tr>
                        <td><strong>${o.protocolo || o.id}</strong></td>
                        <td>${o.titulo}</td>
                        <td style="font-weight: 600; color: var(--primary);">${o.usuario_nome || 'N/A'}</td>
                        <td style="font-size: 0.85rem;">${o.rua || 'N/A'}${o.ponto_referencia ? ` (${o.ponto_referencia})` : ''}</td>
                        ${currentRole==='admin' ? `<td>${o.secretaria_nome || 'N/A'}</td>` : ''}
                        <td>${new Date(o.data).toLocaleString()}</td>
                        <td><span class="badge badge-${s === 'resolvido' ? 'done' : (s === 'em_atendimento' ? 'progress' : 'pending')}">${o.status}</span></td>
                        <td>
                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                ${statusBtn}
                                <button class="btn btn-outline" title="Ver Detalhes" onclick="alert(decodeURIComponent('${encodeURIComponent(o.descricao || '')}'))"><i class="fa-solid fa-eye"></i></button>
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
    document.getElementById('modalResponseTitle').innerText = `Resolver #${id}`;
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
    
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=resolvido`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        if (res.ok) {
            closeModal('modalResponse');
            if (document.getElementById('respFoto')) document.getElementById('respFoto').value = "";
            loadOcorrencias();
            loadDashboard();
            alert("Ocorrência resolvida com sucesso!");
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
        alert("Erro de conexão.");
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
function logout() { localStorage.clear(); window.location.href = 'admin/index.html'; }

async function loadAgendamentos() {
    try {
        const res = await fetch(`${API_URL}/agendamentos`, { headers: { 'Authorization': `Bearer ${getToken()}` } });
        if (res.ok) {
            let list = await res.json();
            if (currentSecId) list = list.filter(a => parseInt(a.secretaria_id) === parseInt(currentSecId));
            
            const container = document.getElementById('agendamentosTableContainer');
            if (list.length === 0) {
                container.innerHTML = '<p style="padding: 2rem; text-align: center;">Nenhum agendamento encontrado.</p>';
                return;
            }

            let html = `<table class="data-table"><thead><tr><th>Protocolo</th><th>Assunto</th><th>Cidadão</th><th>Data/Hora</th><th>Status</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(a => {
                const s = a.status.toLowerCase();
                html += `
                    <tr>
                        <td><strong>${a.protocolo || a.id}</strong></td>
                        <td>${a.assunto}</td>
                        <td>${a.usuario_nome || 'N/A'}</td>
                        <td>${new Date(a.data_hora).toLocaleString()}</td>
                        <td><span class="badge badge-${s === 'confirmado' ? 'done' : (s === 'cancelado' ? 'danger' : 'pending')}">${a.status}</span></td>
                        <td>
                            <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                                ${a.cartao_sus ? `<div style="font-size: 0.75rem; color: var(--primary); font-weight: 600;"><i class="fa-solid fa-address-card"></i> SUS: ${a.cartao_sus}</div>` : ''}
                                <div style="display: flex; gap: 0.5rem;">
                                    ${s === 'pendente' ? `<button class="btn btn-primary" onclick="updateAgendamento('${a.id}', 'Confirmado')">Confirmar</button>` : ''}
                                    ${s === 'confirmado' ? `<button class="btn btn-outline" title="Imprimir Recibo" onclick="imprimirAgendamento('${a.id}')"><i class="fa-solid fa-print"></i></button>` : ''}
                                    ${a.anexo ? `<button class="btn btn-outline" title="Ver Comprovante" onclick="window.open('${MEDIA_URL}/${a.anexo.replace(/\\/g, '/')}', '_blank')"><i class="fa-solid fa-paperclip"></i></button>` : ''}
                                </div>
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

async function updateOcorrenciaStatus(id, status) {
    if (!confirm(`Mudar status para ${status}?`)) return;
    try {
        const res = await fetch(`${API_URL}/ocorrencias/${id}/status?status=${status}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            alert("Status atualizado!");
            loadOcorrencias();
            loadDashboard();
        } else {
            alert("Erro ao atualizar status.");
        }
    } catch(e) { alert("Erro de conexão."); }
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
            alert("Ocorrência resolvida com sucesso!");
            loadOcorrencias();
            loadDashboard();
        } else {
            alert("Erro ao resolver ocorrência.");
        }
    } catch(e) { alert("Erro de conexão."); }
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
            loadDashboard(); // Update metrics too
        } else {
            const err = await res.json();
            alert("Falha ao atualizar status: " + (err.detail || ""));
        }
    } catch(e) { 
        alert("Erro de conexão."); 
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
            
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>Protocolo de Agendamento - ${a.protocolo || a.id}</title>
                    <style>
                        body { font-family: 'Inter', sans-serif; padding: 40px; line-height: 1.6; color: #1e293b; }
                        .header { text-align: center; margin-bottom: 40px; border-bottom: 4px solid #10b981; padding-bottom: 20px; }
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
                        <h1>📌 COMPROVANTE DE AGENDAMENTO</h1>
                        <p>PREFEITURA MUNICIPAL DE COLÔNIA LEOPOLDINA -AL</p>
                    </div>
                    <div class="content">
                        <div class="row"><span class="label">PROTOCOLO:</span> <strong>${a.protocolo || a.id}</strong></div>
                        <div class="row"><span class="label">CIDADÃO:</span> ${a.usuario_nome || 'N/A'}</div>
                        <div class="row"><span class="label">ASSUNTO:</span> ${a.assunto}</div>
                        ${a.motivo ? `<div class="row"><span class="label">MOTIVO:</span> ${a.motivo}</div>` : ''}
                        ${a.cartao_sus ? `<div class="row"><span class="label">CARTÃO SUS:</span> ${a.cartao_sus}</div>` : ''}
                        ${a.acompanhante ? `<div class="row"><span class="label">ACOMPANHANTE:</span> ${a.acompanhante}</div>` : ''}
                        <div class="row" style="background: #dcfce7; padding: 10px; border-radius: 8px;"><span class="label">HORÁRIO MARCADO:</span> <strong style="font-size: 1.2rem; color: #166534;">${new Date(a.data_hora).toLocaleString()}</strong></div>
                        <div class="row"><span class="label">SITUAÇÃO:</span> CONFIRMADO</div>
                    </div>
                    <div class="stamp"><div class="badge">AGENDAMENTO CONFIRMADO</div></div>
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
            
            // Need secretarias map for display
            const sRes = await fetch(`${API_URL}/secretarias`);
            const secs = await sRes.json();
            const sMap = {}; secs.forEach(s => sMap[s.id] = s.nome);
            
            const select = document.getElementById('newAdminSec');
            select.innerHTML = secs.map(s => `<option value="${s.id}">${s.nome}</option>`).join('');

            let html = `<table class="data-table"><thead><tr><th>Nome</th><th>Secretaria</th><th>E-mail</th><th>Telefone</th><th>Ações</th></tr></thead><tbody>`;
            list.forEach(a => {
                html += `
                    <tr>
                        <td>${a.nome}</td>
                        <td><span class="badge badge-progress">${sMap[a.secretaria_id] || 'N/A'}</span></td>
                        <td>${a.email}</td>
                        <td>${a.telefone || '-'}</td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                <button class="btn btn-primary" style="font-size: 0.7rem; padding: 4px 10px;" onclick="openPasswordModal('${a.id}', 'subadmin', '${a.nome}')"><i class="fa-solid fa-key"></i> Trocar Senha</button>
                                <button class="btn" style="background-color: #f59e0b; color: white; border: none; font-size: 0.7rem; padding: 4px 10px; border-radius: 6px; display: flex; align-items: center; gap: 4px;" title="Notificar Pendências" onclick="notificarSubAdmin('${a.id}', '${a.nome}')"><i class="fa-solid fa-bell"></i> Notificar</button>
                                <button class="btn btn-outline" style="color: var(--danger); font-size: 0.7rem; padding: 4px 10px;" onclick="deleteAdmin('${a.id}')"><i class="fa-solid fa-trash"></i></button>
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
        alert("Erro de conexão.");
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
    } catch(e) { alert("Erro ao excluir."); }
}

function openPasswordModal(id, source, nome) {
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
                user_id: parseInt(id),
                source: source,
                new_password: new_password
            })
        });

        if (res.ok) {
            alert("Senha alterada com sucesso!");
            document.getElementById('modalAlterarSenha').style.display = 'none';
        } else {
            const err = await res.json();
            alert(err.detail || "Erro ao alterar senha.");
        }
    } catch(e) {
        alert("Erro de conexão.");
    }
});

// Admin self-password update (from config section)
async function updatePassword() {
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
            alert("Erro: " + (err.detail || "Não foi possível alterar a senha."));
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
        configAvatar.innerHTML = `<img src="${MEDIA_URL}${user.foto_perfil}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
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
                <div class="stat-card" style="margin-bottom: 1rem; border-left: 4px solid var(--primary);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h4 style="margin: 0;">${s.nome}</h4>
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700;">
                            ${s.total_servicos} serviços
                        </span>
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
