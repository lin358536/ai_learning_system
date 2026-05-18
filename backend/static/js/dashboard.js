/* ========== 智途校园 — 能力看板页（雷达图 + 积分 + 排行榜） ========== */
function initDashboardPage() {
  const content = document.getElementById('page-content');
  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/dashboard.css">
    <div class="stat-cards" id="stat-cards">
      <div class="stat-card"><div class="stat-icon green">📖</div><div><div class="stat-value">-</div><div class="stat-label">总积分</div></div></div>
      <div class="stat-card"><div class="stat-icon blue">🏆</div><div><div class="stat-value">-</div><div class="stat-label">排名</div></div></div>
      <div class="stat-card"><div class="stat-icon yellow">👥</div><div><div class="stat-value">-</div><div class="stat-label">总用户</div></div></div>
      <div class="stat-card"><div class="stat-icon red">📊</div><div><div class="stat-value">-</div><div class="stat-label">对话数</div></div></div>
    </div>
    <div class="dashboard-grid">
      <div class="card">
        <div class="card-title">能力雷达图</div>
        <div class="radar-container"><canvas id="radarCanvas" width="320" height="320"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">能力维度</div>
        <div class="skill-list" id="skill-list"></div>
      </div>
    </div>
    <div class="dashboard-grid" style="margin-top:16px;">
      <div class="card">
        <div class="card-title">积分明细</div>
        <div id="points-list"></div>
      </div>
      <div class="card">
        <div class="card-title">积分排行榜</div>
        <div id="rank-list"></div>
      </div>
    </div>`;

  loadData();
}

async function loadData() {
  try {
    const [pointsRes, rankRes, abilitiesRes] = await Promise.all([
      PointsAPI.get(),
      PointsAPI.getRank(10),
      AbilitiesAPI.get(),
    ]);

    // 积分数据
    if (pointsRes.success && pointsRes.data) {
      const d = pointsRes.data;
      const cards = document.getElementById('stat-cards');
      if (cards) {
        cards.children[0].querySelector('.stat-value').textContent = d.total || 0;
        cards.children[1].querySelector('.stat-value').textContent = `第${d.rank || '-'}名`;
        cards.children[2].querySelector('.stat-value').textContent = d.total_users || '-';
      }
      // 积分明细
      const listEl = document.getElementById('points-list');
      if (listEl) {
        if (d.recent && d.recent.length) {
          listEl.innerHTML = `<div class="points-timeline">${d.recent.map(p => `
            <div class="point-item">
              <div class="point-dot"></div>
              <div class="point-info"><div class="point-reason">${p.reason || p.source || '积分变动'}</div><div class="point-time">${formatDate(p.created_at)}</div></div>
              <div class="point-value">+${p.amount || 0}</div>
            </div>`).join('')}</div>`;
        } else {
          listEl.innerHTML = '<div class="empty-state" style="padding:20px;"><div class="empty-text">暂无积分记录</div></div>';
        }
      }
    }

    // 排行榜
    if (rankRes.success && rankRes.data?.leaderboard) {
      const rankEl = document.getElementById('rank-list');
      const user = getUser();
      if (rankEl) {
        rankEl.innerHTML = rankRes.data.leaderboard.map((r, i) => {
          const rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-other';
          const isMe = user && r.name === user.name;
          return `<div class="${isMe ? 'rank-me' : ''}"><div class="rank-item"><div class="rank-num ${rankClass}">${r.rank || i+1}</div><div class="rank-name" ${isMe ? 'style="font-weight:600;"' : ''}>${r.name}${isMe ? '（我）' : ''}</div><div class="rank-score">${r.points} 分</div></div></div>`;
        }).join('');
      }
    }

    // 能力维度数据
    let dimensions = [];
    if (abilitiesRes.success && abilitiesRes.data?.dimensions) {
      dimensions = abilitiesRes.data.dimensions;
    }

    // 绘制雷达图（使用真实数据）
    drawRadar(dimensions);

    // 能力维度列表
    const skillEl = document.getElementById('skill-list');
    if (skillEl) {
      if (dimensions.length > 0) {
        skillEl.innerHTML = dimensions.map(d => {
          const pct = Math.round(d.value * 100);
          const level = pct >= 70 ? 3 : pct >= 40 ? 2 : 1;
          return `<div class="skill-item"><span class="skill-name">${d.name}</span><div class="skill-bar"><div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div></div><span class="skill-level">Lv.${level}</span></div>`;
        }).join('');
      } else {
        skillEl.innerHTML = '<div class="empty-state" style="padding:20px;"><div class="empty-text">暂无能力数据</div></div>';
      }
    }
  } catch (e) {
    showToast('加载看板数据失败：' + e.message, 'error');
  }
}

let radarData = [];
let radarLabels = [];
let radarTooltip = null;

function drawRadar(dimensions) {
  const canvas = document.getElementById('radarCanvas');
  if (!canvas) return;

  if (!dimensions || dimensions.length === 0) {
    radarData = [];
    radarLabels = [];
    radarTooltip = null;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#9CA3AF';
    ctx.font = '13px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('暂无能力数据', canvas.width / 2, canvas.height / 2);
    return;
  }

  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2, R = 110;

  radarData = dimensions.map(d => d.value);
  radarLabels = dimensions.map(d => ({ name: d.name, detail: d.detail, value: d.value }));
  const n = radarData.length;
  const angleStep = (Math.PI * 2) / n;
  const startAngle = -Math.PI / 2;

  function getPoint(i, r) {
    const a = startAngle + i * angleStep;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  }

  // 清除画布
  ctx.clearRect(0, 0, W, H);

  // 背景网格
  for (let level = 1; level <= 4; level++) {
    ctx.beginPath();
    const r = R * (level / 4);
    for (let i = 0; i <= n; i++) {
      const p = getPoint(i % n, r);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    }
    ctx.closePath();
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  // 轴线
  for (let i = 0; i < n; i++) {
    const p = getPoint(i, R);
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(p.x, p.y);
    ctx.strokeStyle = '#E5E7EB'; ctx.stroke();
  }
  // 数据区域
  ctx.beginPath();
  for (let i = 0; i <= n; i++) {
    const p = getPoint(i % n, R * radarData[i % n]);
    if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
  }
  ctx.closePath();
  ctx.fillStyle = 'rgba(42, 157, 143, 0.15)';
  ctx.fill();
  ctx.strokeStyle = '#2A9D8F';
  ctx.lineWidth = 2;
  ctx.stroke();
  // 数据点
  for (let i = 0; i < n; i++) {
    const p = getPoint(i, R * radarData[i]);
    ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#2A9D8F'; ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
  }
  // 标签
  ctx.fillStyle = '#1D3557';
  ctx.font = '12px -apple-system, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (let i = 0; i < n; i++) {
    const p = getPoint(i, R + 24);
    ctx.fillText(radarLabels[i].name, p.x, p.y);
  }

  // 绑定鼠标交互
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let hovered = -1;
    for (let i = 0; i < n; i++) {
      const p = getPoint(i, R * radarData[i]);
      const dist = Math.sqrt((mx - p.x) ** 2 + (my - p.y) ** 2);
      if (dist < 12) {
        hovered = i;
        break;
      }
    }

    if (hovered !== -1) {
      canvas.style.cursor = 'pointer';
      drawRadarTooltip(canvas, hovered, getPoint(hovered, R * radarData[hovered]));
    } else {
      canvas.style.cursor = 'default';
      removeRadarTooltip();
    }
  };

  canvas.onmouseleave = () => {
    removeRadarTooltip();
    canvas.style.cursor = 'default';
  };
}

function drawRadarTooltip(canvas, index, point) {
  removeRadarTooltip();

  const label = radarLabels[index];
  const pct = Math.round(label.value * 100);

  const tooltip = document.createElement('div');
  tooltip.className = 'radar-tooltip';
  tooltip.style.position = 'absolute';
  tooltip.style.background = 'rgba(29, 53, 87, 0.92)';
  tooltip.style.color = '#fff';
  tooltip.style.padding = '8px 12px';
  tooltip.style.borderRadius = '6px';
  tooltip.style.fontSize = '12px';
  tooltip.style.pointerEvents = 'none';
  tooltip.style.whiteSpace = 'nowrap';
  tooltip.style.zIndex = '10';
  tooltip.innerHTML = `<div style="font-weight:600;margin-bottom:2px;">${label.name}</div><div>${label.detail} · ${pct}%</div>`;

  // 先挂载到 DOM，以便读取 offsetWidth
  canvas.parentElement.appendChild(tooltip);
  radarTooltip = tooltip;

  // 再计算位置
  const rect = canvas.parentElement.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const offsetX = canvasRect.left - rect.left + point.x;
  const offsetY = canvasRect.top - rect.top + point.y;

  tooltip.style.left = (offsetX - tooltip.offsetWidth / 2) + 'px';
  tooltip.style.top = (offsetY - tooltip.offsetHeight - 10) + 'px';
}

function removeRadarTooltip() {
  if (radarTooltip) {
    radarTooltip.remove();
    radarTooltip = null;
  }
}

registerRoute('#/learn', (el) => { initDashboardPage(); });
