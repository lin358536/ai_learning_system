/* ========== 智途校园 — 规划管理页 ========== */
function initPlansPage() {
  const content = document.getElementById('page-content');
  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/list.css">
    <div class="list-header">
      <h2>我的规划</h2>
      <button class="btn btn-primary btn-sm" id="btn-goto-chat">+ 去对话创建新规划</button>
    </div>
    <div id="plans-list"><div style="text-align:center;padding:40px;"><div class="spinner" style="margin:0 auto 12px;"></div></div></div>`;

  document.getElementById('btn-goto-chat').addEventListener('click', () => { window.location.hash = '#/chat'; });
  loadPlans();
}

async function loadPlans() {
  const listEl = document.getElementById('plans-list');
  try {
    const result = await PlanAPI.list();
    if (!result.success || !result.data.plans.length) {
      listEl.innerHTML = '<div class="empty-state"><div class="empty-icon"><svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg></div><div class="empty-text">暂无学习规划，去对话页面让小途帮你制定吧</div></div>';
      return;
    }

    listEl.innerHTML = result.data.plans.map(p => {
      const statusTag = p.status === 'confirmed' ? '<span class="tag tag-green">已确认</span>' :
                        p.status === 'draft' ? '<span class="tag tag-yellow">草稿</span>' :
                        '<span class="tag tag-gray">已归档</span>';
      const pct = p.progress || 0;
      const total = p.total_tasks || 0;
      const completed = p.completed_tasks || 0;
      return `
        <div class="plan-card">
          <div class="plan-card-header">
            <span class="plan-card-title" data-id="${p.id}">${p.title || '未命名规划'}</span>
            ${statusTag}
          </div>
          <div class="plan-progress-row">
            <div class="progress-bar" style="flex:1;"><div class="progress-fill" style="width:${pct}%"></div></div>
            <span class="plan-progress-text">${pct}%（${completed}/${total} 任务）</span>
          </div>
          <div class="plan-card-meta">
            <span><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> 总任务 ${total}</span>
            <span><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> 已完成 ${completed}</span>
            <span><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> ${formatDateShort(p.created_at)}</span>
          </div>
          <div class="plan-card-actions">
            <button class="btn btn-outline btn-sm view-plan" data-id="${p.id}">查看详情</button>
            <button class="btn btn-danger-text btn-sm delete-plan" data-id="${p.id}">删除</button>
          </div>
        </div>`;
    }).join('');

    // 绑定事件
    listEl.querySelectorAll('.view-plan, .plan-card-title').forEach(el => {
      el.addEventListener('click', () => showPlanDetail(el.dataset.id));
    });
    listEl.querySelectorAll('.delete-plan').forEach(el => {
      el.addEventListener('click', () => deletePlan(el.dataset.id));
    });
  } catch (e) {
    listEl.innerHTML = `<div style="text-align:center;padding:20px;color:var(--danger);">${e.message}</div>`;
  }
}

async function showPlanDetail(id) {
  let plan;
  try {
    const result = await PlanAPI.getDetail(id);
    if (!result.success) { showToast('获取规划详情失败', 'error'); return; }
    plan = result.data;
  } catch (e) { showToast(e.message, 'error'); return; }

  const content = plan.content || {};
  const tasks = plan.tasks || [];
  const stages = content.stages || [];

  let stagesHtml = '';
  if (stages.length) {
    stagesHtml = stages.map((s, i) => {
      const goals = (s.goals || []).map(g => `<li>${g}</li>`).join('');
      return `<div class="detail-section"><div class="detail-section-title">${s.name || '未命名阶段'}${s.duration ? `（${s.duration}）` : ''}</div>${s.summary ? `<p style="margin:4px 0 8px;color:var(--text-secondary);font-size:0.9em;">${s.summary}</p>` : ''}${goals ? `<ul style="padding-left:20px;">${goals}</ul>` : ''}</div>`;
    }).join('');
  }

  let tasksHtml = '';
  if (tasks.length) {
    const doneCount = tasks.filter(t => t.status === 'completed').length;
    tasksHtml = `<div class="detail-section">
      <div class="detail-section-title">任务清单（<span id="task-counter">${doneCount}</span>/${tasks.length}）</div>
      <div class="plan-progress-row" style="margin-bottom:12px;">
        <div class="progress-bar" style="flex:1;"><div class="progress-fill" id="task-progress-fill" style="width:${tasks.length ? Math.round(doneCount/tasks.length*100) : 0}%"></div></div>
        <span class="plan-progress-text" id="task-progress-text">${tasks.length ? Math.round(doneCount/tasks.length*100) : 0}%</span>
      </div>
      ${tasks.map(t => `
        <div class="task-item" data-task-id="${t.id}" data-status="${t.status}">
          <div class="task-checkbox ${t.status === 'completed' ? 'completed' : ''}">${t.status === 'completed' ? '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' : ''}</div>
          <div class="task-content ${t.status === 'completed' ? 'completed' : ''}">${t.content}</div>
          <div class="task-date">${t.task_date ? formatDateShort(t.task_date) : ''}</div>
        </div>`).join('')}</div>`;
  }

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>${plan.title}</h3>
        <button class="modal-close" id="close-modal">✕</button>
      </div>
      <div class="modal-body">
        ${stagesHtml || '<p style="color:var(--text-muted);">暂无阶段详情</p>'}
        ${tasksHtml}
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.querySelector('#close-modal').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

  // 绑定任务复选框点击事件
  const planId = id;
  modal.querySelectorAll('.task-item').forEach(item => {
    item.querySelector('.task-checkbox').addEventListener('click', async () => {
      const taskId = item.dataset.taskId;
      const isCompleted = item.dataset.status === 'completed';
      const wantComplete = !isCompleted;

      // 立即更新 UI（乐观更新）
      const checkbox = item.querySelector('.task-checkbox');
      const content = item.querySelector('.task-content');
      if (wantComplete) {
        checkbox.classList.add('completed');
        checkbox.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
        content.classList.add('completed');
        item.dataset.status = 'completed';
      } else {
        checkbox.classList.remove('completed');
        checkbox.innerHTML = '';
        content.classList.remove('completed');
        item.dataset.status = 'pending';
      }

      // 更新计数和进度条
      const allItems = modal.querySelectorAll('.task-item');
      const newDone = [...allItems].filter(i => i.dataset.status === 'completed').length;
      const total = allItems.length;
      modal.querySelector('#task-counter').textContent = newDone;
      const pct = Math.round(newDone / total * 100);
      modal.querySelector('#task-progress-fill').style.width = pct + '%';
      modal.querySelector('#task-progress-text').textContent = pct + '%';

      // 调用后端
      try {
        const res = await PlanAPI.toggleTask(planId, taskId, wantComplete);
        if (res.success && res.data.points_earned > 0) {
          showToast(`+${res.data.points_earned} 积分`, 'success');
        }
      } catch (e) {
        // 回滚 UI
        if (!wantComplete) {
          checkbox.classList.add('completed');
          checkbox.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
          content.classList.add('completed');
          item.dataset.status = 'completed';
        } else {
          checkbox.classList.remove('completed');
          checkbox.innerHTML = '';
          content.classList.remove('completed');
          item.dataset.status = 'pending';
        }
        showToast(e.message || '操作失败', 'error');
      }
    });
  });
}

async function deletePlan(id) {
  const ok = await showConfirm('确定要删除这个规划吗？此操作不可撤销。');
  if (!ok) return;
  try {
    await PlanAPI.delete(id);
    showToast('规划已删除', 'success');
    loadPlans();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

registerRoute('#/plans', (el) => { initPlansPage(); });
registerRoute('#/plans/:id', (el, params) => { initPlansPage(); setTimeout(() => showPlanDetail(params.id), 300); });
