/* ========== 智途校园 — 个人中心页 ========== */
function initProfilePage() {
  const content = document.getElementById('page-content');
  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/profile.css">
    <div class="card" style="margin-bottom:16px;">
      <div class="profile-header">
        <div class="profile-avatar-wrapper" id="avatar-upload-trigger" title="点击更换头像">
          <div class="profile-avatar-lg" id="profile-avatar">-</div>
          <div class="avatar-overlay">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </div>
        </div>
        <input type="file" id="avatar-file-input" accept="image/jpeg,image/png,image/gif,image/webp" style="display:none;">
        <div>
          <div class="profile-name" id="profile-name">加载中...</div>
          
        </div>
        <div style="margin-left:auto;" id="profile-points"></div>
      </div>
    </div>
    <div class="profile-grid">
      <div class="card">
        <div class="card-title">基本信息</div>
        <div id="basic-info"><div class="spinner" style="margin:12px auto;"></div></div>
      </div>
      <div class="card">
        <div class="card-title">个人画像</div>
        <div id="profile-data"><div class="spinner" style="margin:12px auto;"></div></div>
      </div>
    </div>
    <div class="profile-actions">
      <button class="btn btn-ghost" id="btn-logout">退出登录</button>
    </div>`;

  document.getElementById('btn-logout').addEventListener('click', () => {
    removeToken();
    window.location.hash = '#/login';
  });

  document.getElementById('avatar-upload-trigger').addEventListener('click', () => {
    document.getElementById('avatar-file-input').click();
  });

  document.getElementById('avatar-file-input').addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await ProfileAPI.uploadAvatar(file);
      if (result.success) {
        showToast('头像更新成功', 'success');
        const user = getUser();
        if (user) {
          user.avatar_url = result.data.avatar_url;
          setUser(user);
        }
        loadProfile();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
    e.target.value = '';
  });

  loadProfile();
}

async function loadProfile() {
  try {
    const [meRes, pointsRes] = await Promise.all([AuthAPI.getMe(), PointsAPI.get()]);

    if (meRes.success && meRes.data) {
      const user = meRes.data;
      const profile = user.profile || {};

      const avatarEl = document.getElementById('profile-avatar');
      if (user.avatar_url) {
        avatarEl.textContent = '';
        avatarEl.style.backgroundImage = `url(${user.avatar_url})`;
        avatarEl.style.backgroundSize = 'cover';
        avatarEl.style.backgroundPosition = 'center';
      } else {
        avatarEl.textContent = user.name ? user.name[0] : '?';
        avatarEl.style.backgroundImage = '';
      }
      document.getElementById('profile-name').textContent = user.name || user.username;
      // document.getElementById('profile-id').textContent = `${user.username}${user.email ? ' · ' + user.email : ''}`;

      // 积分
      if (pointsRes.success && pointsRes.data) {
        document.getElementById('profile-points').innerHTML = `
          <button class="btn btn-outline btn-sm" style="pointer-events:none;">${pointsRes.data.total || 0} 积分</button>`;
      }

      // 基本信息
      document.getElementById('basic-info').innerHTML = `
        <div class="info-row"><span class="info-label">邮箱</span><span class="info-value">${user.email || '未设置'}</span><button class="btn btn-ghost btn-sm" id="btn-edit-email" style="margin-left:auto;">编辑</button></div>
        <div class="info-row"><span class="info-label">注册时间</span><span class="info-value">${formatDateShort(meRes.data.created_at)}</span></div>
        <div class="info-row"><span class="info-label">积分</span><span class="info-value" style="color:var(--primary);font-weight:600;">${pointsRes.data?.total || 0} 分</span></div>`;

      // 画像
      const skills = profile.skills || [];
      const certificates = profile.certificates || [];
      document.getElementById('profile-data').innerHTML = `
        <div class="info-row"><span class="info-label">学历</span><span class="info-value">${profile.education || '未设置'}</span></div>
        <div class="info-row"><span class="info-label">年级</span><span class="info-value">${profile.grade || '未设置'}</span></div>
        <div class="info-row"><span class="info-label">专业</span><span class="info-value">${profile.major || '未设置'}</span></div>
        <div class="info-row"><span class="info-label">目标岗位</span><span class="info-value">${profile.target_job || '未设置'}</span></div>
        <div class="info-row"><span class="info-label">意向行业</span><span class="info-value">${profile.target_industry || '未设置'}</span></div>
        <div class="info-row"><span class="info-label">职业风格</span><span class="info-value">${profile.job_style || '未确定'}</span></div>
        <div class="info-row" style="border:none;"><span class="info-label">技能</span>
          <div class="skill-tags">${skills.length ? skills.map(s => `<span class="skill-tag">${s}</span>`).join('') : '<span style="color:var(--text-muted);font-size:13px;">未设置</span>'}</div>
        </div>
        ${certificates.length ? `<div class="info-row" style="border:none;"><span class="info-label">证书</span>
          <div class="skill-tags">${certificates.map(c => `<span class="skill-tag" style="background:#FEF3C7;color:#92400E;">${c}</span>`).join('')}</div></div>` : ''}
        <div style="text-align:right;margin-top:12px;">
          <button class="btn btn-outline btn-sm" id="btn-edit-profile">编辑画像</button>
        </div>`;

      document.getElementById('btn-edit-profile').addEventListener('click', () => showEditProfileModal(profile));
      document.getElementById('btn-edit-email').addEventListener('click', () => showEditEmailModal(user));
    }
  } catch (e) {
    showToast('加载个人信息失败：' + e.message, 'error');
  }
}

function showEditProfileModal(profile) {
  const skills = profile.skills || [];
  const certificates = profile.certificates || [];

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal" style="width:560px;">
      <div class="modal-header">
        <h3>编辑个人画像</h3>
        <button class="modal-close" id="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="edit-profile-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">学历</label>
              <select class="form-select" id="edit-education">
                <option value="专科" ${profile.education === '专科' ? 'selected' : ''}>专科</option>
                <option value="本科" ${profile.education === '本科' ? 'selected' : ''}>本科</option>
                <option value="硕士" ${profile.education === '硕士' ? 'selected' : ''}>硕士</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">年级</label>
              <select class="form-select" id="edit-grade">
                <option value="">请选择</option>
                <option value="大一" ${profile.grade === '大一' ? 'selected' : ''}>大一</option>
                <option value="大二" ${profile.grade === '大二' ? 'selected' : ''}>大二</option>
                <option value="大三" ${profile.grade === '大三' ? 'selected' : ''}>大三</option>
                <option value="大四" ${profile.grade === '大四' ? 'selected' : ''}>大四</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">专业</label>
              <input class="form-input" id="edit-major" value="${profile.major || ''}" placeholder="如：大数据技术">
            </div>
            <div class="form-group">
              <label class="form-label">职业风格</label>
              <select class="form-select" id="edit-job-style">
                <option value="" ${!profile.job_style ? 'selected' : ''}>未确定</option>
                <option value="稳定型" ${profile.job_style === '稳定型' ? 'selected' : ''}>稳定型</option>
                <option value="进取型" ${profile.job_style === '进取型' ? 'selected' : ''}>进取型</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">目标岗位</label>
              <input class="form-input" id="edit-target-job" value="${profile.target_job || ''}" placeholder="如：数据分析师">
            </div>
            <div class="form-group">
              <label class="form-label">意向行业</label>
              <input class="form-input" id="edit-target-industry" value="${profile.target_industry || ''}" placeholder="如：互联网">
            </div>
          </div>
          <div class="form-group">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
              <input type="checkbox" id="edit-upgrade-intent" ${profile.upgrade_intent ? 'checked' : ''} style="width:auto;">
              <span class="form-label" style="margin:0;">有升本/考研意向</span>
            </label>
          </div>
          <div class="form-group">
            <label class="form-label">技能标签</label>
            <div class="skill-tags" id="edit-skills-tags">
              ${skills.map(s => `<span class="skill-tag">${s}<span class="remove-tag" data-type="skills" data-value="${s}"><svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span></span>`).join('')}
              <button class="add-tag-btn" id="add-skill-btn">+ 添加</button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">证书标签</label>
            <div class="skill-tags" id="edit-certs-tags">
              ${certificates.map(c => `<span class="skill-tag" style="background:#FEF3C7;color:#92400E;">${c}<span class="remove-tag" data-type="certs" data-value="${c}"><svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span></span>`).join('')}
              <button class="add-tag-btn" id="add-cert-btn">+ 添加</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" id="cancel-edit">取消</button>
        <button class="btn btn-primary" id="save-profile">保存</button>
      </div>
    </div>`;
  document.body.appendChild(modal);

  // 管理标签数据
  let editSkills = [...skills];
  let editCerts = [...certificates];

  function refreshTags() {
    document.getElementById('edit-skills-tags').innerHTML = editSkills.map(s => `<span class="skill-tag">${s}<span class="remove-tag" data-type="skills" data-value="${s}"><svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span></span>`).join('') + '<button class="add-tag-btn" id="add-skill-btn"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> 添加</button>';
    document.getElementById('edit-certs-tags').innerHTML = editCerts.map(c => `<span class="skill-tag" style="background:#FEF3C7;color:#92400E;">${c}<span class="remove-tag" data-type="certs" data-value="${c}"><svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span></span>`).join('') + '<button class="add-tag-btn" id="add-cert-btn"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> 添加</button>';
    bindTagEvents();
  }

  function bindTagEvents() {
    modal.querySelectorAll('.remove-tag').forEach(el => {
      el.addEventListener('click', () => {
        const type = el.dataset.type;
        const value = el.dataset.value;
        if (type === 'skills') editSkills = editSkills.filter(s => s !== value);
        else editCerts = editCerts.filter(c => c !== value);
        refreshTags();
      });
    });
    modal.querySelector('#add-skill-btn')?.addEventListener('click', () => addTag('skills'));
    modal.querySelector('#add-cert-btn')?.addEventListener('click', () => addTag('certs'));
  }

  function addTag(type) {
    const value = prompt('请输入标签名称：');
    if (value && value.trim()) {
      if (type === 'skills') { if (!editSkills.includes(value.trim())) editSkills.push(value.trim()); }
      else { if (!editCerts.includes(value.trim())) editCerts.push(value.trim()); }
      refreshTags();
    }
  }

  bindTagEvents();

  // 保存
  document.getElementById('save-profile').addEventListener('click', async () => {
    const data = {
      education: document.getElementById('edit-education').value,
      grade: document.getElementById('edit-grade').value || null,
      major: document.getElementById('edit-major').value.trim() || null,
      target_job: document.getElementById('edit-target-job').value.trim() || null,
      target_industry: document.getElementById('edit-target-industry').value.trim() || null,
      job_style: document.getElementById('edit-job-style').value || null,
      upgrade_intent: document.getElementById('edit-upgrade-intent').checked,
      skills: editSkills,
      certificates: editCerts,
    };

    const saveBtn = document.getElementById('save-profile');
    saveBtn.disabled = true;
    try {
      const result = await ProfileAPI.update(data);
      if (result.success) {
        showToast('画像更新成功', 'success');
        modal.remove();
        // 刷新用户信息
        setUser(getUser()); // 保持用户数据
        initProfilePage();
      }
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });

  document.getElementById('close-modal').addEventListener('click', () => modal.remove());
  document.getElementById('cancel-edit').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

function showEditEmailModal(user) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal" style="width:400px;">
      <div class="modal-header">
        <h3>修改邮箱</h3>
        <button class="modal-close" id="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">邮箱地址</label>
          <input class="form-input" id="edit-email" type="email" value="${user.email || ''}" placeholder="请输入邮箱">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" id="cancel-edit">取消</button>
        <button class="btn btn-primary" id="save-email">保存</button>
      </div>
    </div>`;
  document.body.appendChild(modal);

  document.getElementById('save-email').addEventListener('click', async () => {
    const email = document.getElementById('edit-email').value.trim();
    if (!email) { showToast('请输入邮箱', 'warning'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { showToast('请输入有效的邮箱地址', 'warning'); return; }

    const saveBtn = document.getElementById('save-email');
    saveBtn.disabled = true;
    try {
      const result = await ProfileAPI.updateBasic({ email });
      if (result.success) {
        showToast('邮箱更新成功', 'success');
        const u = getUser();
        if (u) {
          u.email = result.data.email;
          setUser(u);
        }
        modal.remove();
        initProfilePage();
      }
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      saveBtn.disabled = false;
    }
  });

  document.getElementById('close-modal').addEventListener('click', () => modal.remove());
  document.getElementById('cancel-edit').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

registerRoute('#/profile', (el) => { initProfilePage(); });
