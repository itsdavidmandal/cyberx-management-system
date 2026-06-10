let tasks = [];
let projects = [];
let ideas = [];
let guests = [];
let viewDate = new Date();

async function fetchData() {
    try {
        const [tasksRes, projectsRes, ideasRes, guestsRes] = await Promise.all([
            fetch('/api/events/'),
            fetch('/api/projects/'),
            fetch('/api/ideas/'),
            fetch('/api/guests/')
        ]);
        tasks = await tasksRes.json();
        projects = await projectsRes.json();
        ideas = await ideasRes.json();
        guests = await guestsRes.json();

        updateProjectDropdowns();
        updateGuestProjectDropdowns();
        renderDashboard();
        renderIdeas();
        renderKanban();
        renderCalendar();
        renderGuests();
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function updateProjectDropdowns() {
    const select = document.getElementById('project-id-select');
    if (!select) return;
    
    select.innerHTML = '<option value="">Unassigned</option>';
    projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
    });
}

function changeMonth(delta) {
    viewDate.setMonth(viewDate.getMonth() + delta);
    renderCalendar();
}

function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');
    if (viewId === 'calendar') renderCalendar();
    if (viewId === 'kanban') renderKanban();
    if (viewId === 'dashboard') { renderDashboard(); renderIdeas(); }
    if (viewId === 'guests') renderGuests();
}

// Task Modal Logic
function openModal(task = null) {
    const modal = document.getElementById('modal');
    const form = document.getElementById('event-form');
    const modalTitle = document.getElementById('modal-title');
    const statusSelect = document.getElementById('status');
    const projectSelect = document.getElementById('project-id-select');

    if (task) {
        modalTitle.innerText = 'Edit Task';
        document.getElementById('event-id').value = task.id;
        document.getElementById('title').value = task.title;
        document.getElementById('description').value = task.description || '';
        document.getElementById('date').value = task.date;
        document.getElementById('budget').value = task.budget;
        projectSelect.value = task.project_id || "";
        
        const statusToMatch = (task.status || "").toString().trim().toLowerCase();
        for (let i = 0; i < statusSelect.options.length; i++) {
            if (statusSelect.options[i].value.toLowerCase() === statusToMatch) {
                statusSelect.selectedIndex = i;
                break;
            }
        }
    } else {
        modalTitle.innerText = 'Add New Task';
        form.reset();
        document.getElementById('event-id').value = '';
        const localToday = new Date();
        const year = localToday.getFullYear();
        const month = String(localToday.getMonth() + 1).padStart(2, '0');
        const day = String(localToday.getDate()).padStart(2, '0');
        document.getElementById('date').value = `${year}-${month}-${day}`;
    }
    modal.classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

// Project Modal Logic
function openProjectModal(project = null) {
    const modal = document.getElementById('project-modal');
    const title = document.getElementById('project-modal-title');
    const submitBtn = document.getElementById('project-submit-btn');
    const form = document.getElementById('project-form');
    
    if (project) {
        title.textContent = 'Edit Project';
        submitBtn.textContent = 'Save Changes';
        document.getElementById('edit-project-id').value = project.id;
        document.getElementById('project-name').value = project.name;
        document.getElementById('project-description').value = project.description || '';
        document.getElementById('project-start-date').value = project.start_date || '';
        document.getElementById('project-end-date').value = project.end_date || '';
        document.getElementById('project-budget').value = project.budget || 0;
    } else {
        title.textContent = 'Create Project';
        submitBtn.textContent = 'Create Project';
        form.reset();
        document.getElementById('edit-project-id').value = '';
    }
    modal.classList.remove('hidden');
}

function closeProjectModal() {
    document.getElementById('project-modal').classList.add('hidden');
    document.getElementById('project-form').reset();
}

function editProject(id) {
    const project = projects.find(p => p.id === id);
    if (project) openProjectModal(project);
}

document.getElementById('project-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-project-id').value;
    const data = {
        name: document.getElementById('project-name').value,
        description: document.getElementById('project-description').value,
        start_date: document.getElementById('project-start-date').value || null,
        end_date: document.getElementById('project-end-date').value || null,
        budget: parseFloat(document.getElementById('project-budget').value) || 0
    };

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/projects/${id}` : '/api/projects/';

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            closeProjectModal();
            fetchData();
        }
    } catch (error) {
        console.error('Error saving project:', error);
    }
});

// Idea form
document.getElementById('idea-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('idea-title');
    const title = input.value.trim();
    if (!title) return;
    await createIdea(title);
    input.value = '';
});

document.getElementById('event-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('event-id').value;
    const data = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        date: document.getElementById('date').value,
        budget: parseFloat(document.getElementById('budget').value) || 0,
        status: document.getElementById('status').value,
        project_id: parseInt(document.getElementById('project-id-select').value) || null
    };

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/events/${id}` : '/api/events/';

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            closeModal();
            fetchData();
        }
    } catch (error) {
        console.error('Error saving task:', error);
    }
});

async function toggleTask(taskId) {
    try {
        const response = await fetch(`/api/events/${taskId}/toggle`, { method: 'PATCH' });
        if (response.ok) fetchData();
    } catch (error) {
        console.error('Error toggling task:', error);
    }
}

// Drag & Drop Handlers
function handleDragStart(e, taskId) {
    e.dataTransfer.setData('text/plain', taskId);
    e.currentTarget.classList.add('opacity-40');
}

function handleDragEnd(e) {
    e.currentTarget.classList.remove('opacity-40');
}

function handleDragOver(e) {
    e.preventDefault();
    const lane = e.currentTarget;
    lane.classList.add('bg-brand-blue/5');
}

function handleDragLeave(e) {
    const lane = e.currentTarget;
    lane.classList.remove('bg-brand-blue/5');
}

async function handleDrop(e, newStatus) {
    e.preventDefault();
    const lane = e.currentTarget;
    lane.classList.remove('bg-brand-blue/5');
    
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;

    try {
        const response = await fetch(`/api/events/${taskId}/status?status=${encodeURIComponent(newStatus)}`, {
            method: 'PATCH'
        });
        if (response.ok) {
            fetchData();
        }
    } catch (error) {
        console.error('Error updating task status:', error);
    }
}

// Finance Logic
async function openFinanceModal(projectId) {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    document.getElementById('finance-project-id').value = projectId;
    document.getElementById('finance-project-name').textContent = project.name;
    document.getElementById('finance-project-dates').textContent = 
        project.start_date && project.end_date ? `${project.start_date} → ${project.end_date}` : 'No timeline set';
    
    // Set default date to today
    document.getElementById('expense-date').value = new Date().toISOString().split('T')[0];
    
    document.getElementById('finance-modal').classList.remove('hidden');
    fetchExpenses(projectId);
    fetchBudgetLogs(projectId);
}

function closeFinanceModal() {
    document.getElementById('finance-modal').classList.add('hidden');
    document.getElementById('expense-form').reset();
}

async function fetchExpenses(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/expenses/`);
        const expenses = await response.json();
        const project = projects.find(p => p.id === projectId);
        renderExpenses(expenses, project.budget);
    } catch (error) {
        console.error('Error fetching expenses:', error);
    }
}

async function fetchBudgetLogs(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/budget-logs`);
        const logs = await response.json();
        renderBudgetLogs(logs);
    } catch (error) {
        console.error('Error fetching budget logs:', error);
    }
}

function renderBudgetLogs(logs) {
    const container = document.getElementById('budget-history-list');
    container.innerHTML = '';
    
    if (logs.length === 0) {
        container.innerHTML = '<p class="text-[10px] text-gray-400 italic">No budget changes recorded.</p>';
        return;
    }

    logs.forEach(log => {
        const date = new Date(log.change_date).toLocaleString();
        const div = document.createElement('div');
        div.className = 'flex justify-between items-center bg-gray-50 p-2 rounded border border-gray-100';
        div.innerHTML = `
            <span class="text-[10px] font-black text-brand-dark">$${log.amount.toLocaleString()}</span>
            <span class="text-[9px] text-gray-400 font-bold uppercase">${date}</span>
        `;
        container.appendChild(div);
    });
}

function renderExpenses(expenses, projectBudget) {
    const tbody = document.getElementById('expense-list-body');
    const noMsg = document.getElementById('no-expenses-msg');
    tbody.innerHTML = '';
    
    let totalSpent = 0;
    expenses.forEach(exp => {
        totalSpent += exp.amount;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="px-6 py-4 font-bold text-brand-dark text-sm">${exp.name}</td>
            <td class="px-6 py-4 text-gray-500 text-xs">${exp.date}</td>
            <td class="px-6 py-4 font-black text-brand-dark text-sm">$${exp.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td class="px-6 py-4 text-center">
                ${exp.receipt_path ? `
                    <button onclick="previewReceipt('${exp.receipt_path}')" class="text-brand-blue hover:text-brand-dark transition-colors">
                        <i data-lucide="image" class="w-5 h-5 mx-auto"></i>
                    </button>
                ` : '<span class="text-gray-300 text-[10px]">None</span>'}
            </td>
            <td class="px-6 py-4 text-right">
                <button onclick="deleteExpense(${exp.id})" class="text-gray-300 hover:text-brand-red transition-colors">
                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    if (expenses.length === 0) noMsg.classList.remove('hidden');
    else noMsg.classList.add('hidden');

    // Update Overview
    document.getElementById('finance-total-spent').textContent = `$${totalSpent.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById('finance-total-budget').textContent = `$${projectBudget.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    
    const percent = projectBudget > 0 ? Math.min(100, (totalSpent / projectBudget) * 100) : 0;
    document.getElementById('finance-budget-percent').textContent = `${Math.round(percent)}%`;
    const bar = document.getElementById('finance-budget-bar');
    bar.style.width = `${percent}%`;
    
    if (percent > 90) bar.className = 'bg-brand-red h-3 rounded-full transition-all duration-500';
    else if (percent > 70) bar.className = 'bg-yellow-500 h-3 rounded-full transition-all duration-500';
    else bar.className = 'bg-brand-blue h-3 rounded-full transition-all duration-500';

    lucide.createIcons();
}

document.getElementById('expense-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const projectId = document.getElementById('finance-project-id').value;
    const formData = new FormData();
    formData.append('name', document.getElementById('expense-name').value);
    formData.append('amount', document.getElementById('expense-amount').value);
    formData.append('date', document.getElementById('expense-date').value);
    
    const fileInput = document.getElementById('expense-receipt');
    if (fileInput.files[0]) {
        formData.append('receipt', fileInput.files[0]);
    }

    try {
        const response = await fetch(`/api/projects/${projectId}/expenses/`, {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            document.getElementById('expense-form').reset();
            fetchExpenses(projectId);
        }
    } catch (error) {
        console.error('Error saving expense:', error);
    }
});

async function deleteExpense(id) {
    if (confirm('Delete this expense entry?')) {
        try {
            const response = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
            if (response.ok) {
                const projectId = document.getElementById('finance-project-id').value;
                fetchExpenses(projectId);
            }
        } catch (error) { console.error('Error:', error); }
    }
}

function previewReceipt(path) {
    const filename = path.split(/[\\/]/).pop();
    const overlay = document.getElementById('receipt-preview');
    const img = document.getElementById('preview-img');
    img.src = `/api/receipts/${filename}`;
    overlay.classList.remove('hidden');
}

function downloadProjectReport() {
    const projectId = document.getElementById('finance-project-id').value;
    window.location.href = `/api/projects/${projectId}/report`;
}

function calculateDaysLeft(dateStr) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const event = new Date(dateStr + "T00:00:00");
    const diffTime = event - today;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

function createTaskCard(t) {
    const daysLeft = calculateDaysLeft(t.date);
    const card = document.createElement('div');

    const statusColor = 'bg-brand-blue/10 text-brand-blue';
    const borderColor = 'border-brand-dark';
    
    card.className = `bg-white p-6 rounded-2xl shadow-lg border-t-4 ${borderColor} hover:shadow-xl transition-all relative ${t.completed ? 'opacity-75' : ''}`;
    
    card.innerHTML = `
        <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
                <input type="checkbox" ${t.completed ? 'checked' : ''} onchange="toggleTask(${t.id})" class="w-5 h-5 rounded border-gray-300 text-brand-dark focus:ring-brand-blue cursor-pointer">
                <h3 class="text-xl font-black text-brand-dark ${t.completed ? 'line-through text-gray-400' : ''}">${t.title}</h3>
            </div>
            <span class="px-2 py-1 ${statusColor} text-xs font-black uppercase tracking-wider rounded">${t.status}</span>
        </div>
        <p class="text-gray-500 mb-6 text-base leading-relaxed">${t.description || 'No description provided'}</p>
        <div class="flex justify-between items-center text-sm font-bold text-gray-400 uppercase tracking-widest">
            <div class="flex items-center gap-1.5">
                <i data-lucide="clock" class="w-4 h-4"></i>
                <span>${daysLeft < 0 ? 'Past' : daysLeft === 0 ? 'Today' : daysLeft + ' days left'}</span>
            </div>
            <div class="flex items-center gap-1.5">
                <i data-lucide="dollar-sign" class="w-4 h-4"></i>
                <span>${t.budget.toLocaleString()}</span>
            </div>
        </div>
        <div class="mt-6 pt-4 border-t border-gray-50 flex justify-end gap-4">
            <button onclick="editTask(${t.id})" class="text-brand-blue hover:text-brand-dark font-black transition-colors uppercase text-xs">Edit</button>
            <button onclick="deleteTask(${t.id})" class="text-brand-red hover:text-red-800 font-black transition-colors uppercase text-xs">Delete</button>
        </div>
    `;
    return card;
}

function renderDashboard() {
    const monthlyList = document.getElementById('dashboard-list');
    if (!monthlyList) return;

    monthlyList.innerHTML = '';

    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    tasks.forEach(t => {
        const d = new Date(t.date + "T00:00:00");
        if (d.getMonth() === currentMonth && d.getFullYear() === currentYear) {
            monthlyList.appendChild(createTaskCard(t));
        }
    });

    if (monthlyList.children.length === 0) monthlyList.innerHTML = '<p class="text-gray-400 col-span-full py-12 text-center bg-white rounded-2xl border-2 border-dashed border-gray-100 font-bold text-lg">No tasks for this month.</p>';

    lucide.createIcons();
}

// ── Ideas (separate from Tasks) ──────────────────────────
function renderIdeas() {
    const list = document.getElementById('ideation-list');
    if (!list) return;
    list.innerHTML = '';

    ideas.forEach(idea => {
        const card = document.createElement('div');
        card.className = 'bg-white p-5 rounded-2xl shadow-lg border-t-4 border-brand-red hover:shadow-xl transition-all';
        card.innerHTML = `
            <h3 class="text-lg font-black text-brand-dark mb-2">${idea.title}</h3>
            <p class="text-gray-500 text-sm leading-relaxed mb-4">${idea.description || 'No description'}</p>
            <div class="flex justify-end gap-3 pt-3 border-t border-gray-50">
                <button onclick="editIdea(${idea.id})" class="text-brand-blue hover:text-brand-dark font-black transition-colors uppercase text-xs">Edit</button>
                <button onclick="deleteIdea(${idea.id})" class="text-brand-red hover:text-red-800 font-black transition-colors uppercase text-xs">Delete</button>
            </div>
        `;
        list.appendChild(card);
    });

    if (ideas.length === 0) {
        list.innerHTML = '<p class="text-gray-400 col-span-full py-12 text-center bg-white rounded-2xl border-2 border-dashed border-gray-100 font-bold text-lg">No ideas yet. Add one above!</p>';
    }

    lucide.createIcons();
}

async function createIdea(title) {
    try {
        const res = await fetch('/api/ideas/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description: '' })
        });
        if (res.ok) { fetchData(); }
    } catch (e) { console.error('Error creating idea:', e); }
}

async function editIdea(id) {
    const idea = ideas.find(i => i.id === id);
    if (!idea) return;
    const title = prompt('Edit idea title:', idea.title);
    if (title === null) return;
    const description = prompt('Edit description (optional):', idea.description || '');
    if (description === null) return;
    try {
        const res = await fetch(`/api/ideas/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description })
        });
        if (res.ok) { fetchData(); }
    } catch (e) { console.error('Error updating idea:', e); }
}

async function deleteIdea(id) {
    if (!confirm('Delete this idea?')) return;
    try {
        const res = await fetch(`/api/ideas/${id}`, { method: 'DELETE' });
        if (res.ok) { fetchData(); }
    } catch (e) { console.error('Error deleting idea:', e); }
}
// ──────────────────────────────────────────────────────────

function renderKanban() {
    const container = document.getElementById('kanban-swimlanes');
    if (!container) return;
    container.innerHTML = '';

    const groups = { null: { name: 'Unassigned', tasks: [] } };
    projects.forEach(p => groups[p.id] = { name: p.name, tasks: [] });
    tasks.forEach(t => {
        const gid = t.project_id || 'null';
        if (groups[gid]) groups[gid].tasks.push(t);
    });

    Object.entries(groups).forEach(([id, group]) => {
        if (group.tasks.length === 0 && id === 'null') return;

        const project = projects.find(p => p.id == id) || { name: 'Unassigned' };
        const dateDisplay = project.start_date && project.end_date 
            ? `<span class="text-[10px] font-black text-brand-blue uppercase tracking-widest bg-brand-blue/10 px-2 py-1 rounded ml-2">${project.start_date} → ${project.end_date}</span>`
            : '';

        const swimlane = document.createElement('div');
        swimlane.className = 'bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden';
        swimlane.innerHTML = `
            <div class="bg-brand-dark/5 px-8 py-5 border-b border-gray-100 flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <h3 class="text-2xl font-black text-brand-dark flex items-center gap-3">
                        <i data-lucide="layers" class="w-7 h-7 text-brand-blue"></i> ${group.name}
                    </h3>
                    ${dateDisplay}
                    ${id !== 'null' ? `
                        <div class="flex gap-2 ml-4">
                            <button onclick="openFinanceModal(${id})" class="bg-brand-blue/10 text-brand-blue hover:bg-brand-blue hover:text-white px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-1">
                                <i data-lucide="dollar-sign" class="w-3 h-3"></i> Finance
                            </button>
                            <button onclick="editProject(${id})" class="text-gray-400 hover:text-brand-blue p-1 transition-colors" title="Edit Project">
                                <i data-lucide="settings" class="w-5 h-5"></i>
                            </button>
                            <button onclick="deleteProject(${id})" class="text-gray-400 hover:text-brand-red p-1 transition-colors" title="Delete Project">
                                <i data-lucide="trash-2" class="w-5 h-5"></i>
                            </button>
                        </div>
                    ` : ''}
                </div>
                <span class="bg-brand-dark text-white px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest">${group.tasks.length} tasks</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-0 divide-x divide-gray-50">
                ${['To-Do', 'In Progress', 'Done'].map(status => `
                    <div class="p-6 min-h-[250px] bg-white transition-colors"
                         ondragover="handleDragOver(event)"
                         ondragleave="handleDragLeave(event)"
                         ondrop="handleDrop(event, '${status}')">
                        <div class="flex justify-between items-center mb-6">
                            <h4 class="text-xs font-black text-gray-300 uppercase tracking-[0.2em]">${status}</h4>
                            <button onclick="quickAddTask(${id}, '${status}')" class="text-gray-300 hover:text-brand-blue p-1 transition-colors" title="Quick add task">
                                <i data-lucide="plus-circle" class="w-4 h-4"></i>
                            </button>
                        </div>
                        <div id="lane-${id}-${status.replace(' ', '-')}" class="space-y-4"></div>
                        <div id="quickadd-${id}-${status.replace(' ', '-')}" class="mt-3"></div>
                    </div>
                `).join('')}
            </div>
        `;
        container.appendChild(swimlane);

        group.tasks.forEach(t => {
            const laneId = `lane-${id}-${t.status.replace(' ', '-')}`;
            const lane = document.getElementById(laneId);
            if (lane) {
                const card = document.createElement('div');
                card.className = `bg-gray-50 p-5 rounded-2xl border-l-4 cursor-pointer hover:bg-white hover:shadow-lg transition-all ${t.completed ? 'opacity-50' : ''}`;
                card.setAttribute('draggable', 'true');
                card.addEventListener('dragstart', (e) => handleDragStart(e, t.id));
                card.addEventListener('dragend', handleDragEnd);
                
                const statusClean = t.status.toLowerCase();
                if (statusClean === 'in progress') card.classList.add('border-brand-blue');
                else if (statusClean === 'done') card.classList.add('border-brand-dark');
                else card.classList.add('border-gray-200');

                card.innerHTML = `
                    <div class="flex items-start gap-3">
                        <input type="checkbox" ${t.completed ? 'checked' : ''} onclick="event.stopPropagation(); toggleTask(${t.id})" class="mt-1 w-4 h-4 rounded border-gray-300 text-brand-dark focus:ring-brand-blue">
                        <h4 class="font-bold text-brand-dark text-base leading-tight ${t.completed ? 'line-through text-gray-400' : ''}">${t.title}</h4>
                    </div>
                    <div class="flex justify-between items-center mt-4">
                        <p class="text-[10px] text-gray-400 uppercase font-black tracking-widest">${t.date}</p>
                        <p class="text-sm font-black text-brand-dark">$${t.budget.toLocaleString()}</p>
                    </div>
                `;
                card.onclick = () => editTask(t.id);
                lane.appendChild(card);
            }
        });
    });
    lucide.createIcons();
}

function quickAddTask(projectId, status) {
    const laneKey = `quickadd-${projectId}-${status.replace(' ', '-')}`;
    const slot = document.getElementById(laneKey);
    if (!slot) return;

    // If form already open, close it
    if (slot.children.length > 0) {
        slot.innerHTML = '';
        return;
    }

    const form = document.createElement('div');
    form.className = 'flex gap-2 items-center';
    form.innerHTML = `
        <input type="text" id="quick-title-${laneKey}" placeholder="Task title..." class="flex-1 border-2 border-gray-100 rounded-lg bg-gray-50 px-3 py-2 text-xs focus:ring-brand-blue focus:border-brand-blue outline-none">
        <button onclick="submitQuickTask(${projectId}, '${status}', '${laneKey}')" class="bg-brand-dark text-white px-3 py-2 rounded-lg text-xs font-black hover:bg-brand-blue transition-colors">Add</button>
        <button onclick="document.getElementById('${laneKey}').innerHTML=''" class="text-gray-300 hover:text-brand-red p-1 transition-colors">
            <i data-lucide="x" class="w-3 h-3"></i>
        </button>
    `;
    slot.appendChild(form);
    lucide.createIcons();
    document.getElementById(`quick-title-${laneKey}`).focus();
}

async function submitQuickTask(projectId, status, laneKey) {
    const input = document.getElementById(`quick-title-${laneKey}`);
    if (!input) return;
    const title = input.value.trim();
    if (!title) return;

    const today = new Date();
    const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    try {
        const res = await fetch('/api/events/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                description: '',
                date: dateStr,
                budget: 0,
                status,
                completed: false,
                project_id: projectId
            })
        });
        if (res.ok) { fetchData(); }
    } catch (e) { console.error('Error creating task:', e); }
}

function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    const display = document.getElementById('current-month-display');
    if (!grid || !display) return;

    grid.innerHTML = '';
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    display.innerText = viewDate.toLocaleString('default', { month: 'long', year: 'numeric' });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const prevMonthLastDay = new Date(year, month, 0).getDate();

    for (let i = firstDay; i > 0; i--) grid.appendChild(createCalendarCell(prevMonthLastDay - i + 1, false));

    const today = new Date();
    for (let d = 1; d <= daysInMonth; d++) {
        const isToday = today.getDate() === d && today.getMonth() === month && today.getFullYear() === year;
        const cell = createCalendarCell(d, true, isToday);
        const dateString = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        
        // Render Projects
        const container = cell.querySelector('.event-container');
        if (container) {
            projects.filter(p => {
                if (!p.start_date) return false;
                if (p.start_date === dateString) return true;
                if (p.end_date && dateString > p.start_date && dateString <= p.end_date) return true;
                return false;
            }).forEach(p => {
                const pill = document.createElement('div');
                pill.className = `mt-1.5 px-2.5 py-1.5 bg-brand-dark text-white text-[10px] font-black uppercase tracking-wider rounded-md truncate cursor-pointer hover:opacity-80 transition-opacity`;
                pill.innerText = `PROJ: ${p.name}`;
                pill.onclick = (e) => { e.stopPropagation(); editProject(p.id); };
                container.appendChild(pill);
            });
        }

        tasks.filter(t => t.date === dateString).forEach(t => {
            const pill = document.createElement('div');
            const pillColor = 'bg-brand-blue text-white';
            pill.className = `mt-1.5 px-2.5 py-1.5 ${pillColor} text-[10px] font-black uppercase tracking-wider rounded-md truncate cursor-pointer hover:opacity-80 transition-opacity ${t.completed ? 'line-through opacity-40' : ''}`;
            pill.innerText = t.title;
            pill.onclick = (e) => { e.stopPropagation(); editTask(t.id); };
            cell.querySelector('.event-container').appendChild(pill);
        });

        cell.onclick = () => { openModal(); document.getElementById('date').value = dateString; };
        grid.appendChild(cell);
    }

    const remaining = 42 - grid.children.length;
    for (let i = 1; i <= remaining; i++) grid.appendChild(createCalendarCell(i, false));
    lucide.createIcons();
}

function createCalendarCell(day, isCurrentMonth, isToday = false) {
    const cell = document.createElement('div');
    cell.className = `min-h-[130px] p-3 bg-white flex flex-col border-r border-b border-gray-50 ${isCurrentMonth ? '' : 'bg-gray-50/50 text-gray-300'}`;
    if (isToday) cell.classList.add('bg-brand-blue/5');
    cell.innerHTML = `<span class="text-sm font-black ${isToday ? 'bg-brand-dark text-white w-8 h-8 flex items-center justify-center rounded-xl shadow-lg' : ''}">${day}</span><div class="event-container mt-2 space-y-1.5 overflow-y-auto max-h-[95px]"></div>`;
    return cell;
}

function editTask(id) {
    const task = tasks.find(t => t.id === id);
    if (task) openModal(task);
}

async function deleteProject(id) {
    if (confirm('Permanently delete this project? All tasks within it will become "Unassigned".')) {
        try {
            const response = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
            if (response.ok) fetchData();
        } catch (error) { console.error('Error deleting project:', error); }
    }
}

async function deleteTask(id) {
    if (confirm('Permanently delete this task?')) {
        try {
            const response = await fetch(`/api/events/${id}`, { method: 'DELETE' });
            if (response.ok) fetchData();
        } catch (error) { console.error('Error:', error); }
    }
}

function exportCSV() { window.location.href = '/api/events/export/csv'; }
function exportPDF() { window.location.href = '/api/events/export/pdf'; }

// Guest Management Logic
function updateGuestProjectDropdowns() {
    const filters = ['guest-event-filter', 'guest-project-id'];
    filters.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        const currentVal = select.value;
        
        if (id === 'guest-event-filter') {
            select.innerHTML = '<option value="">All Projects</option><option value="unassigned">Unassigned Only</option>';
        } else {
            select.innerHTML = '<option value="">Unassigned</option>';
        }

        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            select.appendChild(opt);
        });
        select.value = currentVal;
    });
}

function openGuestModal(guest = null) {
    const modal = document.getElementById('guest-modal');
    const form = document.getElementById('guest-form');
    const title = document.getElementById('guest-modal-title');
    const submitBtn = document.getElementById('guest-submit-btn');

    updateGuestProjectDropdowns();

    if (guest) {
        title.textContent = 'Edit Invitee';
        submitBtn.textContent = 'Save Changes';
        document.getElementById('edit-guest-id').value = guest.id;
        document.getElementById('guest-name').value = guest.name;
        document.getElementById('guest-project-id').value = guest.project_id || '';
        document.getElementById('guest-email').value = guest.email || '';
        document.getElementById('guest-phone').value = guest.phone || '';
        document.getElementById('guest-org').value = guest.organization || '';
        document.getElementById('guest-status').value = guest.status;
    } else {
        title.textContent = 'Add Invitee';
        submitBtn.textContent = 'Save Invitee';
        form.reset();
        document.getElementById('edit-guest-id').value = '';
    }
    modal.classList.remove('hidden');
}

function closeGuestModal() {
    document.getElementById('guest-modal').classList.add('hidden');
}

document.getElementById('guest-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-guest-id').value;
    const data = {
        name: document.getElementById('guest-name').value,
        project_id: parseInt(document.getElementById('guest-project-id').value) || null,
        email: document.getElementById('guest-email').value || null,
        phone: document.getElementById('guest-phone').value || null,
        organization: document.getElementById('guest-org').value || null,
        status: document.getElementById('guest-status').value
    };

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/guests/${id}` : `/api/guests/`;

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            closeGuestModal();
            fetchData();
        }
    } catch (error) {
        console.error('Error saving guest:', error);
    }
});

function renderGuests() {
    const tbody = document.getElementById('guest-list-body');
    const noMsg = document.getElementById('no-guests-msg');
    const searchInput = document.getElementById('guest-search');
    const filterInput = document.getElementById('guest-event-filter');
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const projectFilter = filterInput ? filterInput.value : '';

    if (!tbody) return;
    tbody.innerHTML = '';

    const filtered = guests.filter(g => {
        const matchesSearch = g.name.toLowerCase().includes(searchTerm) || 
                             (g.email && g.email.toLowerCase().includes(searchTerm)) ||
                             (g.organization && g.organization.toLowerCase().includes(searchTerm));
        
        let matchesProject = true;
        if (projectFilter === 'unassigned') {
            matchesProject = !g.project_id;
        } else if (projectFilter !== '') {
            matchesProject = g.project_id == projectFilter;
        }
        
        return matchesSearch && matchesProject;
    });

    filtered.forEach(g => {
        const project = projects.find(p => p.id === g.project_id) || { name: 'Unassigned' };
        const tr = document.createElement('tr');
        
        let statusClass = 'bg-gray-100 text-gray-600';
        if (g.status === 'Confirmed') statusClass = 'bg-green-100 text-green-700';
        else if (g.status === 'Declined') statusClass = 'bg-red-100 text-red-700';
        else if (g.status === 'Attended') statusClass = 'bg-brand-blue/10 text-brand-blue';

        tr.innerHTML = `
            <td class="px-6 py-4">
                <div class="font-bold text-brand-dark">${g.name}</div>
            </td>
            <td class="px-6 py-4">
                <div class="text-xs font-medium ${g.project_id ? 'text-brand-blue' : 'text-gray-400 italic'}">${project.name}</div>
            </td>
            <td class="px-6 py-4">
                <div class="text-xs text-gray-500">${g.email || '-'}</div>
                <div class="text-[10px] text-gray-400">${g.phone || ''}</div>
            </td>
            <td class="px-6 py-4">
                <div class="text-xs text-gray-500">${g.organization || '-'}</div>
            </td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${statusClass}">${g.status}</span>
            </td>
            <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                    <button onclick="editGuest(${g.id})" class="text-gray-300 hover:text-brand-blue transition-colors">
                        <i data-lucide="edit-3" class="w-4 h-4"></i>
                    </button>
                    <button onclick="deleteGuest(${g.id})" class="text-gray-300 hover:text-brand-red transition-colors">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });

    if (filtered.length === 0) noMsg.classList.remove('hidden');
    else noMsg.classList.add('hidden');
    
    lucide.createIcons();
}

function editGuest(id) {
    const guest = guests.find(g => g.id === id);
    if (guest) openGuestModal(guest);
}

async function deleteGuest(id) {
    if (confirm('Remove this invitee?')) {
        try {
            const response = await fetch(`/api/guests/${id}`, { method: 'DELETE' });
            if (response.ok) fetchData();
        } catch (error) { console.error('Error:', error); }
    }
}

// Init
fetchData();
