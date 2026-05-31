let events = [];

async function fetchEvents() {
    try {
        const response = await fetch('/api/events/');
        events = await response.json();
        renderDashboard();
        renderKanban();
    } catch (error) {
        console.error('Error fetching events:', error);
    }
}

function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');
}

function openModal(event = null) {
    const modal = document.getElementById('modal');
    const form = document.getElementById('event-form');
    const modalTitle = document.getElementById('modal-title');

    if (event) {
        modalTitle.innerText = 'Edit Event';
        document.getElementById('event-id').value = event.id;
        document.getElementById('title').value = event.title;
        document.getElementById('description').value = event.description;
        document.getElementById('date').value = event.date;
        document.getElementById('budget').value = event.budget;
        document.getElementById('status').value = event.status;
    } else {
        modalTitle.innerText = 'Add New Event';
        form.reset();
        document.getElementById('event-id').value = '';
    }

    modal.classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

document.getElementById('event-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('event-id').value;
    const data = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        date: document.getElementById('date').value,
        budget: parseFloat(document.getElementById('budget').value) || 0,
        status: document.getElementById('status').value
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
            fetchEvents();
        }
    } catch (error) {
        console.error('Error saving event:', error);
    }
});

function calculateDaysLeft(eventDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const event = new Date(eventDate);
    const diffTime = event - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

function renderDashboard() {
    const list = document.getElementById('dashboard-list');
    list.innerHTML = '';
    
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    const monthlyEvents = events.filter(e => {
        const d = new Date(e.date);
        return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
    });

    if (monthlyEvents.length === 0) {
        list.innerHTML = '<p class="text-gray-500 col-span-full">No events planned for this month.</p>';
        return;
    }

    monthlyEvents.sort((a, b) => new Date(a.date) - new Date(b.date)).forEach(e => {
        const daysLeft = calculateDaysLeft(e.date);
        const card = document.createElement('div');
        card.className = 'bg-white p-6 rounded-lg shadow-md border-t-4 border-indigo-500 hover:shadow-lg transition-shadow';
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-xl font-bold">${e.title}</h3>
                <span class="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-semibold rounded">${e.status}</span>
            </div>
            <p class="text-gray-600 mb-4 text-sm">${e.description || 'No description'}</p>
            <div class="flex justify-between items-center text-sm text-gray-500">
                <div class="flex items-center gap-1">
                    <i data-lucide="clock" class="w-4 h-4"></i>
                    <span>${daysLeft < 0 ? 'Past' : daysLeft === 0 ? 'Today' : daysLeft + ' days left'}</span>
                </div>
                <div class="flex items-center gap-1">
                    <i data-lucide="dollar-sign" class="w-4 h-4"></i>
                    <span>${e.budget.toLocaleString()}</span>
                </div>
            </div>
            <div class="mt-4 pt-4 border-t flex justify-end gap-2">
                <button onclick='editEvent(${JSON.stringify(e)})' class="text-blue-600 hover:text-blue-800 text-sm">Edit</button>
                <button onclick="deleteEvent(${e.id})" class="text-red-600 hover:text-red-800 text-sm">Delete</button>
            </div>
        `;
        list.appendChild(card);
    });
    lucide.createIcons();
}

function renderKanban() {
    const columns = {
        'To-Do': document.getElementById('kanban-todo'),
        'In Progress': document.getElementById('kanban-progress'),
        'Done': document.getElementById('kanban-done')
    };

    Object.values(columns).forEach(col => col.innerHTML = '');

    events.forEach(e => {
        const card = document.createElement('div');
        card.className = 'bg-white p-4 rounded shadow-sm border-l-4 border-gray-400 cursor-pointer hover:bg-gray-50';
        card.innerHTML = `
            <h4 class="font-semibold">${e.title}</h4>
            <p class="text-xs text-gray-500">${e.date}</p>
        `;
        card.onclick = () => editEvent(e);
        if (columns[e.status]) {
            columns[e.status].appendChild(card);
        }
    });
}

function editEvent(event) {
    openModal(event);
}

async function deleteEvent(id) {
    if (confirm('Are you sure you want to delete this event?')) {
        try {
            const response = await fetch(`/api/events/${id}`, { method: 'DELETE' });
            if (response.ok) fetchEvents();
        } catch (error) {
            console.error('Error deleting event:', error);
        }
    }
}

// Initial Load
fetchEvents();
