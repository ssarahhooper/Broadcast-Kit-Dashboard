// static/js/calendar.js
function initKitCalendar(options) {
  const {
    headerId = "kitcalHeader",
    gridId = "kitcalGrid",
    labelId = "monthYearLabel",
    prevBtnId = "prevWeekBtn",
    nextBtnId = "nextWeekBtn",
    todayBtnId = "todayBtn",
    weekStartsOnSunday = true,
    demoEvents = []
  } = options || {};

  function toDateOnly(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d, 0, 0, 0, 0);
  }
  function addDays(date, n) {
    const d = new Date(date);
    d.setDate(d.getDate() + n);
    return d;
  }
  function startOfWeek(date) {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    const day = d.getDay();
    const diff = weekStartsOnSunday ? day : (day === 0 ? 6 : day - 1);
    d.setDate(d.getDate() - diff);
    return d;
  }
  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }
  function formatDow(d) {
    return ["SUN","MON","TUES","WED","THURS","FRI","SAT"][d.getDay()];
  }
  function monthYearForWeek(weekStart) {
    const end = addDays(weekStart, 6);
    const m1 = weekStart.toLocaleString(undefined, { month: "short" });
    const m2 = end.toLocaleString(undefined, { month: "short" });
    const y1 = weekStart.getFullYear();
    const y2 = end.getFullYear();

    if (y1 === y2 && m1 === m2) return `${m1} ${y1}`;
    if (y1 === y2) return `${m1}–${m2} ${y1}`;
    return `${m1} ${y1} – ${m2} ${y2}`;
  }
  function dayColumnIndex(weekStart, dateObj) {
    const msPerDay = 24 * 60 * 60 * 1000;
    const diffDays = Math.round((dateObj - weekStart) / msPerDay);
    if (diffDays < 0 || diffDays > 6) return null;
    return diffDays + 1;
  }

  const header = document.getElementById(headerId);
  const grid = document.getElementById(gridId);
  const label = document.getElementById(labelId);

  if (!header || !grid || !label) return;

  let currentWeekStart = startOfWeek(new Date());

  function renderWeek(weekStart) {
    label.textContent = monthYearForWeek(weekStart);
    header.innerHTML = "";
    grid.innerHTML = "";

    for (let i = 0; i < 7; i++) {
      const day = addDays(weekStart, i);
      const box = document.createElement("div");
      box.className = "daybox";
      box.innerHTML = `
        <div class="daybox__dow">${formatDow(day)}</div>
        <div class="daybox__dom">${day.getDate()}</div>
      `;
      header.appendChild(box);
    }

    demoEvents.forEach(ev => {
      const s = toDateOnly(ev.start);
      const e = toDateOnly(ev.end);

      let c1 = dayColumnIndex(weekStart, s);
      let c2 = dayColumnIndex(weekStart, e);
      if (c1 === null && c2 === null) return;

      const startCol = c1 ?? 1;
      const endColInclusive = c2 ?? 7;

      const colStart = clamp(startCol, 1, 7);
      const colEnd = clamp(endColInclusive + 1, 2, 8);

      const row = clamp(ev.kit, 1, 11);

      const bar = document.createElement("div");
      bar.className = "kitEvent";
      bar.style.background = ev.color;
      bar.style.gridRow = String(row);
      bar.style.gridColumn = `${colStart} / ${colEnd}`;
      bar.title = `Kit ${ev.kit}: ${ev.start} → ${ev.end}`;
      grid.appendChild(bar);
    });
  }

  document.getElementById(prevBtnId)?.addEventListener("click", () => {
    currentWeekStart = addDays(currentWeekStart, -7);
    renderWeek(currentWeekStart);
  });
  document.getElementById(nextBtnId)?.addEventListener("click", () => {
    currentWeekStart = addDays(currentWeekStart, 7);
    renderWeek(currentWeekStart);
  });
  document.getElementById(todayBtnId)?.addEventListener("click", () => {
    currentWeekStart = startOfWeek(new Date());
    renderWeek(currentWeekStart);
  });

  renderWeek(currentWeekStart);
}