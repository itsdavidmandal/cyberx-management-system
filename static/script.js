let tasks = [];
let projects = [];
let viewDate = new Date();

// Helper: Check if status is "Ideation"
function isIdeation(status) {
    if (status === null || status === undefined) return false;
    return status.toString().trim().toLowerCase() === 'ideation';
}

async function fetchData() {
    try {
        const [tasksRes, projectsRes] = await Promise.all([
            fetch('/api/events/'),
            fetch('/api/projects/')
        ]);
        tasks = await tasksRes.json();
        projects = await projectsRes.json();
        
        updateProjectDropdowns();
        renderDashboard();
        renderKanban();
        renderCalendar();
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
    if (viewId === 'dashboard') renderDashboard();
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
function openProjectModal() {
    document.getElementById('project-modal').classList.remove('hidden');
}

function closeProjectModal() {
    document.getElementById('project-modal').classList.add('hidden');
    document.getElementById('project-form').reset();
}

document.getElementById('project-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        name: document.getElementById('project-name').value,
        description: document.getElementById('project-description').value
    };

    try {
        const response = await fetch('/api/projects/', {
            method: 'POST',
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
    const ideation = isIdeation(t.status);
    const statusColor = ideation ? 'bg-yellow-100 text-yellow-700' : 'bg-indigo-100 text-indigo-700';
    const borderColor = ideation ? 'border-yellow-400' : 'border-indigo-500';
    
    card.className = `bg-white p-6 rounded-lg shadow-md border-t-4 ${borderColor} hover:shadow-lg transition-shadow relative ${t.completed ? 'opacity-75' : ''}`;
    
    card.innerHTML = `
        <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
                <input type="checkbox" ${t.completed ? 'checked' : ''} onchange="toggleTask(${t.id})" class="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                <h3 class="text-xl font-bold ${t.completed ? 'line-through text-gray-400' : ''}">${t.title}</h3>
            </div>
            <span class="px-2 py-1 ${statusColor} text-xs font-semibold rounded">${t.status}</span>
        </div>
        <p class="text-gray-600 mb-4 text-sm line-clamp-2">${t.description || 'No description'}</p>
        <div class="flex justify-between items-center text-sm text-gray-500">
            <div class="flex items-center gap-1">
                <i data-lucide="clock" class="w-4 h-4"></i>
                <span>${daysLeft < 0 ? 'Past' : daysLeft === 0 ? 'Today' : daysLeft + ' days left'}</span>
            </div>
            <div class="flex items-center gap-1">
                <i data-lucide="dollar-sign" class="w-4 h-4"></i>
                <span>${t.budget.toLocaleString()}</span>
            </div>
        </div>
        <div class="mt-4 pt-4 border-t flex justify-end gap-2">
            <button onclick="editTask(${t.id})" class="text-blue-600 hover:text-blue-800 text-sm font-medium">Edit</button>
            <button onclick="deleteTask(${t.id})" class="text-red-600 hover:text-red-800 text-sm font-medium">Delete</button>
        </div>
    `;
    return card;
}

function renderDashboard() {
    const monthlyList = document.getElementById('dashboard-list');
    const ideationList = document.getElementById('ideation-list');
    if (!monthlyList || !ideationList) return;
    
    monthlyList.innerHTML = '';
    ideationList.innerHTML = '';
    
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    tasks.forEach(t => {
        if (isIdeation(t.status)) {
            ideationList.appendChild(createTaskCard(t));
        } else {
            const d = new Date(t.date + "T00:00:00");
            if (d.getMonth() === currentMonth && d.getFullYear() === currentYear) {
                monthlyList.appendChild(createTaskCard(t));
            }
        }
    });

    if (monthlyList.children.length === 0) monthlyList.innerHTML = '<p class="text-gray-500 col-span-full py-4 text-center">No tasks confirmed for this month.</p>';
    if (ideationList.children.length === 0) ideationList.innerHTML = '<p class="text-gray-500 col-span-full py-4 text-center">No ideation tasks yet.</p>';
    
    lucide.createIcons();
}

function renderKanban() {
    const container = document.getElementById('kanban-swimlanes');
    if (!container) return;
    container.innerHTML = '';

    // Group tasks by project
    const groups = { null: { name: 'Unassigned', tasks: [] } };
    projects.forEach(p => groups[p.id] = { name: p.name, tasks: [] });
    tasks.forEach(t => {
        const gid = t.project_id || 'null';
        if (groups[gid]) groups[gid].tasks.push(t);
    });

    Object.entries(groups).forEach(([id, group]) => {
        if (group.tasks.length === 0 && id === 'null') return; // Skip empty unassigned

        const swimlane = document.createElement('div');
        swimlane.className = 'bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden';
        swimlane.innerHTML = `
            <div class="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 class="text-lg font-bold text-gray-700 flex items-center gap-2">
                    <i data-lucide="folder" class="w-5 h-5 text-indigo-500"></i> ${group.name}
                </h3>
                <span class="text-sm text-gray-500">${group.tasks.length} tasks</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-0 divide-x divide-gray-100">
                ${['Ideation', 'To-Do', 'In Progress', 'Done'].map(status => `
                    <div class="p-4 min-h-[200px] bg-gray-50/30">
                        <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">${status}</h4>
                        <div id="lane-${id}-${status.replace(' ', '-')}" class="space-y-3"></div>
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
                card.className = `bg-white p-4 rounded shadow-sm border-l-4 cursor-pointer hover:bg-gray-50 transition-colors ${t.completed ? 'opacity-60' : ''}`;
                
                const statusClean = t.status.toLowerCase();
                if (statusClean === 'ideation') card.classList.add('border-yellow-400');
                else if (statusClean === 'in progress') card.classList.add('border-blue-400');
                else if (statusClean === 'done') card.classList.add('border-green-400');
                else card.classList.add('border-gray-300');

                card.innerHTML = `
                    <div class="flex items-start gap-2">
                        <input type="checkbox" ${t.completed ? 'checked' : ''} onclick="event.stopPropagation(); toggleTask(${t.id})" class="mt-1 w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500">
                        <h4 class="font-semibold text-gray-800 leading-tight ${t.completed ? 'line-through text-gray-400' : ''}">${t.title}</h4>
                    </div>
                    <div class="flex justify-between items-center mt-3">
                        <p class="text-[10px] text-gray-500 uppercase font-medium tracking-tighter">${t.date}</p>
                        <p class="text-xs font-bold text-gray-700">$${t.budget.toLocaleString()}</p>
                    </div>
                `;
                card.onclick = () => editTask(t.id);
                lane.appendChild(card);
            }
        });
    });
    lucide.createIcons();
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
        
        tasks.filter(t => t.date === dateString).forEach(t => {
            const pill = document.createElement('div');
            const pillColor = isIdeation(t.status) ? 'bg-yellow-100 text-yellow-700' : 'bg-indigo-100 text-indigo-700';
            pill.className = `mt-1 px-2 py-0.5 ${pillColor} text-[10px] font-medium rounded truncate cursor-pointer hover:opacity-80 ${t.completed ? 'line-through opacity-60' : ''}`;
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
    cell.className = `min-h-[100px] p-2 bg-white flex flex-col border-r border-b border-gray-100 ${isCurrentMonth ? '' : 'bg-gray-50 text-gray-400'}`;
    if (isToday) cell.classList.add('bg-indigo-50');
    cell.innerHTML = `<span class="text-sm font-semibold ${isToday ? 'bg-indigo-600 text-white w-6 h-6 flex items-center justify-center rounded-full' : ''}">${day}</span><div class="event-container mt-1 space-y-1 overflow-y-auto max-h-[80px]"></div>`;
    return cell;
}

function editTask(id) {
    const task = tasks.find(t => t.id === id);
    if (task) openModal(task);
}

async function deleteTask(id) {
    if (confirm('Delete this task?')) {
        try {
            const response = await fetch(`/api/events/${id}`, { method: 'DELETE' });
            if (response.ok) fetchData();
        } catch (error) { console.error('Error:', error); }
    }
}

function exportCSV() { window.location.href = '/api/events/export/csv'; }
function exportPDF() { window.location.href = '/api/events/export/pdf'; }

// Init
fetchData();
