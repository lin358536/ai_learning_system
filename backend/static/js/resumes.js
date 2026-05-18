/* ========== 智途校园 — 简历管理页 ========== */
function initResumesPage() {
  const content = document.getElementById('page-content');
  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/list.css">
    <div class="list-header">
      <h2>我的简历</h2>
      <button class="btn btn-primary btn-sm" id="btn-goto-chat">+ 去对话创建新简历</button>
    </div>
    <div id="resumes-list"><div style="text-align:center;padding:40px;"><div class="spinner" style="margin:0 auto 12px;"></div></div></div>`;

  document.getElementById('btn-goto-chat').addEventListener('click', () => { window.location.hash = '#/chat'; });
  loadResumes();
}

async function loadResumes() {
  const listEl = document.getElementById('resumes-list');
  try {
    const result = await ResumeAPI.list();
    if (!result.success || !result.data.resumes.length) {
      listEl.innerHTML = '<div class="empty-state"><div class="empty-icon">📄</div><div class="empty-text">暂无简历，去对话页面让小途帮你生成吧</div></div>';
      return;
    }

    listEl.innerHTML = result.data.resumes.map(r => `
      <div class="resume-card">
        <div class="resume-icon">📄</div>
        <div class="resume-info">
          <div class="resume-title">${r.title || '未命名简历'}</div>
          <div class="resume-date">创建于 ${formatDateShort(r.created_at)}</div>
        </div>
        <div class="resume-actions">
          <button class="btn btn-outline btn-sm view-resume" data-id="${r.id}">查看</button>
          <button class="btn btn-danger-text btn-sm delete-resume" data-id="${r.id}">删除</button>
        </div>
      </div>`).join('');

    listEl.querySelectorAll('.view-resume').forEach(el => {
      el.addEventListener('click', () => showResumeDetail(el.dataset.id));
    });
    listEl.querySelectorAll('.delete-resume').forEach(el => {
      el.addEventListener('click', () => deleteResume(el.dataset.id));
    });
  } catch (e) {
    listEl.innerHTML = `<div style="text-align:center;padding:20px;color:var(--danger);">${e.message}</div>`;
  }
}

async function showResumeDetail(id) {
  let resume;
  try {
    const result = await ResumeAPI.getDetail(id);
    if (!result.success) { showToast('获取简历失败', 'error'); return; }
    resume = result.data;
  } catch (e) { showToast(e.message, 'error'); return; }

  // 简历内容可能是 JSON 对象或字符串
  let contentHtml = '';
  const c = resume.content;
  let parsed = c;
  if (typeof c === 'string') {
    try { parsed = JSON.parse(c); } catch { parsed = null; }
  }
  if (parsed && typeof parsed === 'object') {
    // 新结构：有 basic / skills / experience 字段
    if (parsed.basic !== undefined || parsed.skills !== undefined || parsed.experience !== undefined) {
      contentHtml = renderResumeJSON(parsed);
    } else if (parsed.markdown) {
      // 旧格式兜底
      contentHtml = renderMarkdown(parsed.markdown);
    } else {
      contentHtml = renderResumeJSON(parsed);
    }
  } else {
    contentHtml = renderMarkdown(typeof c === 'string' ? c : '');
  }

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal" style="width:700px;">
      <div class="modal-header">
        <h3>${resume.title}</h3>
        <button class="modal-close" id="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="resume-content">${contentHtml || '<p style="color:var(--text-muted);">暂无内容</p>'}</div>
      </div>
      <div class="modal-footer">
        <span style="flex:1;font-size:12px;color:var(--text-muted);">创建于 ${formatDate(resume.created_at)}</span>
        <button class="btn btn-outline btn-sm" onclick="navigator.clipboard.writeText(this.closest('.modal').querySelector('.resume-content').innerText).then(()=>showToast('已复制到剪贴板','success'))">复制内容</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.querySelector('#close-modal').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

function renderResumeJSON(data) {
  if (!data) return '';

  const basic      = data.basic      || {};
  const education  = data.education  || [];
  const skills     = data.skills     || [];
  const experience = data.experience || [];
  const certs      = data.certs      || [];
  const summary    = data.summary    || '';

  const esc = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  let html = '';

  /* ── 头部：姓名 + 基本信息 ── */
  const name = esc(basic['姓名'] || '');
  html += `<div class="resume-header" style="margin-bottom:20px;padding-bottom:16px;border-bottom:2px solid var(--primary);">`;
  if (name) html += `<h1 style="margin:0 0 6px;font-size:1.6rem;">${name}</h1>`;
  const metaItems = [basic['学历'], basic['专业'], basic['学校']].filter(Boolean).map(esc);
  if (metaItems.length) html += `<p style="margin:0 0 6px;color:var(--text-secondary);">${metaItems.join(' · ')}</p>`;
  const intentItem = esc(basic['求职意向'] || '');
  if (intentItem) html += `<p style="margin:0 0 4px;"><span style="background:var(--primary-10,rgba(99,102,241,.12));color:var(--primary);padding:2px 8px;border-radius:4px;font-size:0.85rem;">求职意向：${intentItem}</span></p>`;
  const contactItem = esc(basic['联系方式'] || '');
  if (contactItem) html += `<p style="margin:4px 0 0;font-size:0.85rem;color:var(--text-secondary);">📞 ${contactItem}</p>`;
  html += `</div>`;

  /* ── 教育背景 ── */
  if (education.length) {
    html += `<h2 style="font-size:1rem;border-left:3px solid var(--primary);padding-left:8px;margin:16px 0 8px;">教育背景</h2>`;
    education.forEach(e => {
      html += `<div style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:baseline;">
        <span><strong>${esc(e['学校'])}</strong>　${esc(e['专业'])}　${esc(e['学历'])}</span>
        <span style="color:var(--text-muted);font-size:0.85rem;">${esc(e['时间'])}</span>
      </div>`;
    });
  }

  /* ── 专业技能 ── */
  if (skills.length) {
    html += `<h2 style="font-size:1rem;border-left:3px solid var(--primary);padding-left:8px;margin:16px 0 8px;">专业技能</h2>`;
    html += `<ul style="margin:0;padding-left:20px;line-height:1.9;">`;
    skills.forEach(s => { html += `<li style="color:var(--text-secondary);">${esc(s)}</li>`; });
    html += `</ul>`;
  }

  /* ── 项目经历 ── */
  if (experience.length) {
    html += `<h2 style="font-size:1rem;border-left:3px solid var(--primary);padding-left:8px;margin:16px 0 8px;">项目经历</h2>`;
    experience.forEach(exp => {
      html += `<div style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
          <strong>${esc(exp['名称'])}</strong>
          <span style="color:var(--text-muted);font-size:0.85rem;">${esc(exp['时间'])}</span>
        </div>`;
      if (exp['角色']) html += `<p style="margin:0 0 4px;font-size:0.85rem;color:var(--primary);">角色：${esc(exp['角色'])}</p>`;
      if (exp['描述']) html += `<p style="margin:0 0 4px;color:var(--text-secondary);font-size:0.9rem;">${esc(exp['描述'])}</p>`;
      if (exp['成果']) html += `<p style="margin:0;font-size:0.85rem;color:var(--success,#22c55e);">✓ ${esc(exp['成果'])}</p>`;
      html += `</div>`;
    });
  }

  /* ── 证书与比赛 ── */
  if (certs.length) {
    html += `<h2 style="font-size:1rem;border-left:3px solid var(--primary);padding-left:8px;margin:16px 0 8px;">证书与比赛</h2>`;
    html += `<ul style="margin:0;padding-left:20px;line-height:1.9;">`;
    certs.forEach(cert => {
      const institution = esc(cert['等级/颁发机构'] || '');
      const time = esc(cert['时间'] || '');
      html += `<li style="color:var(--text-secondary);">
        <strong>${esc(cert['名称'])}</strong>`;
      if (institution) html += `　<span style="font-size:0.85rem;">${institution}</span>`;
      if (time) html += `　<span style="color:var(--text-muted);font-size:0.82rem;">${time}</span>`;
      html += `</li>`;
    });
    html += `</ul>`;
  }

  /* ── 自我评价 ── */
  if (summary) {
    html += `<h2 style="font-size:1rem;border-left:3px solid var(--primary);padding-left:8px;margin:16px 0 8px;">自我评价</h2>`;
    html += `<p style="color:var(--text-secondary);font-size:0.9rem;line-height:1.8;margin:0;">${esc(summary)}</p>`;
  }

  return html;
}

async function deleteResume(id) {
  const ok = await showConfirm('确定要删除这份简历吗？此操作不可撤销。');
  if (!ok) return;
  try {
    await ResumeAPI.delete(id);
    showToast('简历已删除', 'success');
    loadResumes();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

registerRoute('#/resumes', (el) => { initResumesPage(); });
