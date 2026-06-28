// bubbles — poll /progress and render each torrent's state
const list = document.getElementById("download-list");

async function poll() {
    try {
        const res = await fetch("/progress");
        const data = await res.json();   // { id: {name, pct, percent, state}, ... }
        render(data);
    } catch (err) {
        console.error("progress poll failed", err);
    }
}

function render(data) {
    const ids = Object.keys(data);

    if (ids.length === 0) {
        list.innerHTML = '<li class="empty">No active downloads.</li>';
        return;
    }

    list.innerHTML = ids.map((id) => {
        const t = data[id];
        const pct = Math.round(t.percent ?? t.pct ?? 0);
        return `
            <li>
                <span class="name">${escapeHtml(t.name)} — ${escapeHtml(t.state)}</span>
                <div class="bar"><span style="width:${pct}%"></span></div>
            </li>
        `;
    }).join("");
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

poll();                 // run once immediately
setInterval(poll, 250); // then every 500ms
