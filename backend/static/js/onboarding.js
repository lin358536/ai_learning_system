/* ========== 智途校园 — 首次登录画像引导页 ========== */

function initOnboardingPage(contentEl) {
  let currentStep = 1;
  const totalSteps = 3;
  let animating = false;

  const data = {
    education: '',
    grade: '',
    major: '',
    target_job: '',
    target_industry: '',
    job_style: '',
    upgrade_intent: false,
    skills: [],
    certificates: []
  };

  function render() {
    contentEl.innerHTML = `
      <div class="onboarding-wrapper">
        <div class="onboarding-header">
          <div class="onboarding-steps">
            ${Array.from({ length: totalSteps }, (_, i) => `
              <div class="step-dot ${i + 1 === currentStep ? 'active' : ''} ${i + 1 < currentStep ? 'completed' : ''}"></div>
            `).join('')}
          </div>
          <div class="onboarding-nav-top">
            <button class="onboarding-btn-back" id="ob-btn-back" ${currentStep === 1 ? 'disabled' : ''}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              上一步
            </button>
            <button class="onboarding-btn-skip" id="ob-btn-skip">跳过</button>
          </div>
        </div>
        <div class="onboarding-content" id="ob-content">
          ${renderStep(currentStep)}
        </div>
        <div class="onboarding-footer" id="ob-footer">
          ${currentStep > 1 ? '<button class="btn btn-outline" id="ob-btn-prev"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg> 上一步</button>' : '<div></div>'}
          <button class="btn btn-primary" id="ob-btn-next">${currentStep === totalSteps ? '完成' : '继续'}</button>
        </div>
      </div>`;

    bindEvents();
    restoreData();
  }

  function renderStep(step) {
    switch (step) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      default: return '';
    }
  }

  function renderStep1() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
        </div>
        <div class="onboarding-description">让我们先了解你的学习背景</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">学历</label>
            <div class="segmented-control" id="ob-education">
              ${['专科', '本科', '硕士'].map(v => `
                <button class="segmented-option ${data.education === v ? 'selected' : ''}" data-value="${v}">${v}</button>
              `).join('')}
            </div>
          </div>
          <div>
            <label class="onboarding-field-label">年级</label>
            <div class="segmented-control" id="ob-grade">
              ${['大一', '大二', '大三', '大四'].map(v => `
                <button class="segmented-option ${data.grade === v ? 'selected' : ''}" data-value="${v}">${v}</button>
              `).join('')}
            </div>
          </div>
          <div>
            <label class="onboarding-field-label">专业</label>
            <input class="form-input" id="ob-major" type="text" placeholder="如：大数据技术" value="${data.major || ''}">
          </div>
        </div>
      </div>`;
  }

  function renderStep2() {
    const styles = [
      { value: '稳定型', desc: '追求稳定，偏好国企/事业单位' },
      { value: '进取型', desc: '追求成长，偏好互联网/创业' },
      { value: '未确定', desc: '还在探索，想了解更多' }
    ];
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
        </div>
        <div class="onboarding-description">你的职业目标是什么？</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">目标岗位</label>
            <input class="form-input" id="ob-target-job" type="text" placeholder="如：数据分析师" value="${data.target_job || ''}">
          </div>
          <div>
            <label class="onboarding-field-label">意向行业</label>
            <input class="form-input" id="ob-target-industry" type="text" placeholder="如：互联网" value="${data.target_industry || ''}">
          </div>
          <div>
            <label class="onboarding-field-label">职业风格</label>
            <div class="cards-horizontal" id="ob-job-style">
              ${styles.map(s => `
                <div class="card-option ${data.job_style === s.value ? 'selected' : ''}" data-value="${s.value}">
                  <div class="card-option-label">${s.value}</div>
                  <div class="card-option-desc">${s.desc}</div>
                </div>
              `).join('')}
            </div>
          </div>
          <div>
            <div class="toggle-wrapper">
              <span class="toggle-label">升本/考研意向</span>
              <button class="toggle-switch ${data.upgrade_intent ? 'active' : ''}" id="ob-toggle-upgrade" role="switch" aria-checked="${data.upgrade_intent}"></button>
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderStep3() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
        </div>
        <div class="onboarding-description">展示你的技能与证书</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">技能标签</label>
            <div class="tag-input-area" id="ob-skills-area">
              ${data.skills.map(s => `
                <span class="tag-item">${s}<button class="tag-remove" data-tag="${s}" data-list="skills">×</button></span>
              `).join('')}
              <input class="tag-input-field" id="ob-skills-input" placeholder="输入技能后按回车" autocomplete="off">
            </div>
          </div>
          <div>
            <label class="onboarding-field-label">证书标签</label>
            <div class="tag-input-area" id="ob-certs-area">
              ${data.certificates.map(c => `
                <span class="tag-item">${c}<button class="tag-remove" data-tag="${c}" data-list="certificates">×</button></span>
              `).join('')}
              <input class="tag-input-field" id="ob-certs-input" placeholder="输入证书后按回车" autocomplete="off">
            </div>
          </div>
        </div>
      </div>`;
  }

  function bindEvents() {
    document.getElementById('ob-btn-next').addEventListener('click', onNext);
    document.getElementById('ob-btn-skip').addEventListener('click', onSkip);

    const prevBtn = document.getElementById('ob-btn-prev');
    if (prevBtn) prevBtn.addEventListener('click', onPrev);

    const backBtn = document.getElementById('ob-btn-back');
    if (backBtn) backBtn.addEventListener('click', onPrev);

    if (currentStep === 1) {
      bindSegmented('ob-education', 'education');
      bindSegmented('ob-grade', 'grade');
      document.getElementById('ob-major').addEventListener('input', (e) => { data.major = e.target.value; });
    }

    if (currentStep === 2) {
      document.getElementById('ob-target-job').addEventListener('input', (e) => { data.target_job = e.target.value; });
      document.getElementById('ob-target-industry').addEventListener('input', (e) => { data.target_industry = e.target.value; });
      bindCardSelect('ob-job-style', 'job_style');
      document.getElementById('ob-toggle-upgrade').addEventListener('click', () => {
        data.upgrade_intent = !data.upgrade_intent;
        document.getElementById('ob-toggle-upgrade').classList.toggle('active');
        document.getElementById('ob-toggle-upgrade').setAttribute('aria-checked', data.upgrade_intent);
      });
    }

    if (currentStep === 3) {
      bindTagInput('ob-skills-input', 'skills');
      bindTagInput('ob-certs-input', 'certificates');
      document.querySelectorAll('.tag-remove').forEach(btn => {
        btn.addEventListener('click', () => {
          const tag = btn.dataset.tag;
          const list = btn.dataset.list;
          data[list] = data[list].filter(t => t !== tag);
          render();
        });
      });
    }
  }

  function bindSegmented(containerId, field) {
    document.querySelectorAll(`#${containerId} .segmented-option`).forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll(`#${containerId} .segmented-option`).forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        data[field] = btn.dataset.value;
      });
    });
  }

  function bindCardSelect(containerId, field) {
    document.querySelectorAll(`#${containerId} .card-option`).forEach(card => {
      card.addEventListener('click', () => {
        document.querySelectorAll(`#${containerId} .card-option`).forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        data[field] = card.dataset.value;
      });
    });
  }

  function bindTagInput(inputId, list) {
    const input = document.getElementById(inputId);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = input.value.trim();
        if (val && !data[list].includes(val)) {
          data[list].push(val);
          render();
        }
      }
    });
    input.addEventListener('blur', () => {
      const val = input.value.trim();
      if (val && !data[list].includes(val)) {
        data[list].push(val);
        render();
      }
    });
  }

  function restoreData() {
    const profiles = JSON.parse(localStorage.getItem('ob_profile') || '{}');
    Object.keys(profiles).forEach(k => {
      if (k in data) data[k] = profiles[k];
    });
  }

  function saveToLocal() {
    localStorage.setItem('ob_profile', JSON.stringify(data));
  }

  async function autoSave() {
    saveToLocal();
    try {
      await ProfileAPI.update(data);
    } catch (e) {
      console.warn('画像自动保存失败:', e);
    }
  }

  async function onNext() {
    if (animating) return;
    if (currentStep === totalSteps) {
      await autoSave();
      localStorage.removeItem('ob_profile');
      window.location.hash = '#/chat';
      return;
    }
    await autoSave();
    currentStep++;
    animating = true;
    render();
    animating = false;
  }

  function onPrev() {
    if (animating || currentStep <= 1) return;
    currentStep--;
    render();
  }

  function onSkip() {
    localStorage.removeItem('ob_profile');
    window.location.hash = '#/chat';
  }

  render();
}

registerRoute('#/onboarding', (el) => {
  initOnboardingPage(el);
});
