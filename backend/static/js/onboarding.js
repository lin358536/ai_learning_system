/* ========== 智途校园 — 首次登录画像引导页 ========== */

function initOnboardingPage(contentEl) {
  let currentStep = 1;
  const totalSteps = 8;
  let transitioning = false;
  let skipped = false;

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

  function buildShell() {
    const isSpecial = currentStep === 1 || currentStep === totalSteps;
    return `
      <div class="onboarding-wrapper">
        <div class="onboarding-header" id="ob-header" ${isSpecial ? 'style="display:none"' : ''}>
          <div class="step-counter" id="ob-step-counter">第 1 / ${totalSteps} 步</div>
          <div class="onboarding-steps" id="ob-steps">
            ${Array.from({ length: totalSteps }, (_, i) => `
              <div class="step-dot ${i === 0 ? 'active' : ''}" data-step="${i + 1}"></div>
            `).join('')}
          </div>

        </div>
        <div class="onboarding-content" id="ob-content">
          <div class="step-slide forward-enter" id="ob-step-slide">
            ${renderStepContent(currentStep)}
          </div>
        </div>
        <div class="onboarding-footer" id="ob-footer">
          <div class="onboarding-footer-inner">
            <button class="onboarding-btn-back" id="ob-btn-back" disabled style="display:none">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              上一步
            </button>
            <button class="onboarding-btn-skip" id="ob-btn-skip" style="display:none">跳过引导</button>
            <button class="btn btn-primary" id="ob-btn-next">开始填写</button>
          </div>
        </div>
      </div>`;
  }

  function renderStepContent(step) {
    switch (step) {
      case 1: return renderIntro();
      case 2: return renderStep1();
      case 3: return renderStep2();
      case 4: return renderStep3();
      case 5: return renderStep4();
      case 6: return renderStep5();
      case 7: return renderStep6();
      case 8: return renderThankYou();
      default: return '';
    }
  }

  function renderIntro() {
    return `
      <div class="onboarding-card" style="text-align:center">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24" width="80" height="80"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        </div>
        <div class="onboarding-description">欢迎来到智途校园</div>
        <div class="onboarding-sub-description" style="max-width:380px;margin:0 auto 32px">
          为了给你提供更精准的个性化学习规划，我们需要了解你的一些基本信息。<br><br>
          整个过程大约需要 2 分钟，请放心填写。
        </div>
      </div>`;
  }

  function renderStep1() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
        </div>
        <div class="onboarding-description">你的学历是什么？</div>
        <div class="onboarding-sub-description">选择你的当前学历，我们将为你推荐适合的学习路径</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">学历</label>
            <div class="segmented-control" id="ob-education">
              ${['专科', '本科', '硕士'].map(v => `
                <button class="segmented-option ${data.education === v ? 'selected' : ''}" data-value="${v}">${v}</button>
              `).join('')}
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderStep2() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        </div>
        <div class="onboarding-description">你在读什么专业？</div>
        <div class="onboarding-sub-description">目前就读于哪个年级？帮助我们了解你的学习阶段</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">专业名称</label>
            <span class="onboarding-field-hint">你的主修或专业方向</span>
            <input class="form-input" id="ob-major" type="text" placeholder="如：大数据技术、软件工程" value="${data.major || ''}">
          </div>
          <div>
            <label class="onboarding-field-label">年级</label>
            <span class="onboarding-field-hint">当前所在的年级</span>
            <div class="segmented-control" id="ob-grade">
              ${['大一', '大二', '大三', '大四'].map(v => `
                <button class="segmented-option ${data.grade === v ? 'selected' : ''}" data-value="${v}">${v}</button>
              `).join('')}
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderStep3() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
        </div>
        <div class="onboarding-description">你的理想职业是什么？</div>
        <div class="onboarding-sub-description">告诉我们你的目标，我们将为你定制专属学习规划</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">目标岗位</label>
            <span class="onboarding-field-hint">毕业后你最想从事的岗位</span>
            <input class="form-input" id="ob-target-job" type="text" placeholder="如：数据分析师、前端开发" value="${data.target_job || ''}">
          </div>
          <div>
            <label class="onboarding-field-label">意向行业</label>
            <span class="onboarding-field-hint">你最感兴趣的行业领域</span>
            <input class="form-input" id="ob-target-industry" type="text" placeholder="如：互联网、金融、医疗" value="${data.target_industry || ''}">
          </div>
        </div>
      </div>`;
  }

  function renderStep4() {
    const styles = [
      { value: '稳定型', desc: '追求稳定，偏好国企、事业单位', icon: '🏛' },
      { value: '进取型', desc: '追求成长，偏好互联网、创业', icon: '🚀' },
      { value: '未确定', desc: '还在探索，想了解更多可能', icon: '🔍' }
    ];
    return `
      <div class="onboarding-card onboarding-card--step4">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
        </div>
        <div class="onboarding-description">你倾向哪种职业风格？</div>
        <div class="onboarding-sub-description">了解你的偏好，帮你找到最适合的发展方向</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">职业风格</label>
            <span class="onboarding-field-hint">选择最符合你性格的职业倾向</span>
            <div class="cards-horizontal" id="ob-job-style">
              ${styles.map(s => `
                <div class="card-option ${data.job_style === s.value ? 'selected' : ''}" data-value="${s.value}">
                  <div style="font-size:28px;margin-bottom:6px">${s.icon}</div>
                  <div class="card-option-label">${s.value}</div>
                  <div class="card-option-desc">${s.desc}</div>
                </div>
              `).join('')}
            </div>
          </div>
          <div>
            <div class="toggle-wrapper">
              <div class="toggle-label-group">
                <span class="toggle-label">升本 / 考研意向</span>
                <span class="toggle-desc">是否有继续深造的打算？</span>
              </div>
              <button class="toggle-switch ${data.upgrade_intent ? 'active' : ''}" id="ob-toggle-upgrade" role="switch" aria-checked="${data.upgrade_intent}"></button>
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderStep5() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
        </div>
        <div class="onboarding-description">你掌握了哪些技能？</div>
        <div class="onboarding-sub-description">添加你已经掌握的技能，帮助我们了解你的能力基础</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">技能标签</label>
            <span class="onboarding-field-hint">输入技能名称后按回车键添加</span>
            <div class="tag-input-area" id="ob-skills-area">
              ${data.skills.map(s => `
                <span class="tag-item">${s}<button class="tag-remove" data-tag="${s}" data-list="skills">×</button></span>
              `).join('')}
              <input class="tag-input-field" id="ob-skills-input" placeholder="如：Python、数据分析、Photoshop" autocomplete="off">
            </div>
            <div class="tag-hint">提示：可以添加编程语言、设计工具、语言能力等</div>
          </div>
        </div>
      </div>`;
  }

  function renderStep6() {
    return `
      <div class="onboarding-card">
        <div class="onboarding-icon">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
        </div>
        <div class="onboarding-description">你获得了哪些证书？</div>
        <div class="onboarding-sub-description">添加你已获得的证书，让学习规划更精准</div>
        <div class="onboarding-form">
          <div>
            <label class="onboarding-field-label">证书标签</label>
            <span class="onboarding-field-hint">输入证书名称后按回车键添加</span>
            <div class="tag-input-area" id="ob-certs-area">
              ${data.certificates.map(c => `
                <span class="tag-item">${c}<button class="tag-remove" data-tag="${c}" data-list="certificates">×</button></span>
              `).join('')}
              <input class="tag-input-field" id="ob-certs-input" placeholder="如：英语四级、计算机二级" autocomplete="off">
            </div>
            <div class="tag-hint">提示：包括语言证书、职业资格证书、竞赛奖项等</div>
          </div>
        </div>
      </div>`;
  }

  function renderThankYou() {
    const msg = skipped
      ? '已跳过信息填写。你可以随时在「我的」页面补充和修改信息。'
      : '感谢你的填写！你的信息已保存。后续如需更改，可前往「我的」页面修改。';
    const icon = skipped
      ? '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M8 12l2 2 4-4"/></svg>'
      : '<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
    return `
      <div class="onboarding-card" style="text-align:center">
        <div class="onboarding-icon" style="color:var(--primary);width:80px;height:80px">
          ${icon}
        </div>
        <div class="onboarding-description" style="margin-bottom:16px">
          ${skipped ? '已跳过信息填写' : '信息填写完成'}
        </div>
        <div class="onboarding-sub-description" style="max-width:360px;margin:0 auto;font-size:15px;color:var(--text-secondary)">
          ${msg}
        </div>
      </div>`;
  }

  function updateStepUI(direction) {
    const slideEl = document.getElementById('ob-step-slide');
    slideEl.className = 'step-slide';
    slideEl.innerHTML = renderStepContent(currentStep);
    void slideEl.offsetHeight;
    slideEl.classList.add(direction === 'forward' ? 'forward-enter' : 'backward-enter');

    const isSpecial = currentStep === 1 || currentStep === totalSteps;
    const header = document.getElementById('ob-header');

    if (isSpecial) {
      header.style.display = 'none';
    } else {
      header.style.display = '';
      document.getElementById('ob-step-counter').textContent = `第 ${currentStep - 1} / ${totalSteps - 2} 步`;
      document.querySelectorAll('#ob-steps .step-dot').forEach(dot => {
        const s = parseInt(dot.dataset.step, 10);
        dot.className = 'step-dot';
        if (s === currentStep) dot.classList.add('active');
        else if (s < currentStep) dot.classList.add('completed');
      });
    }

    const backBtn = document.getElementById('ob-btn-back');
    const skipBtn = document.getElementById('ob-btn-skip');
    if (currentStep > 1 && currentStep < totalSteps) {
      backBtn.style.display = '';
      backBtn.disabled = false;
      skipBtn.style.display = '';
    } else {
      backBtn.style.display = 'none';
      skipBtn.style.display = 'none';
    }

    const nextBtn = document.getElementById('ob-btn-next');
    if (currentStep === 1) {
      nextBtn.textContent = '开始填写';
    } else if (currentStep === totalSteps) {
      nextBtn.textContent = '进入智途校园';
    } else {
      nextBtn.textContent = '继续';
    }

    bindStepEvents();
  }

  function bindStepEvents() {
    if (currentStep === 2) {
      bindSegmented('ob-education', 'education');
    }

    if (currentStep === 3) {
      document.getElementById('ob-major').addEventListener('input', (e) => { data.major = e.target.value; });
      bindSegmented('ob-grade', 'grade');
    }

    if (currentStep === 4) {
      document.getElementById('ob-target-job').addEventListener('input', (e) => { data.target_job = e.target.value; });
      document.getElementById('ob-target-industry').addEventListener('input', (e) => { data.target_industry = e.target.value; });
    }

    if (currentStep === 5) {
      bindCardSelect('ob-job-style', 'job_style');
      document.getElementById('ob-toggle-upgrade').addEventListener('click', () => {
        data.upgrade_intent = !data.upgrade_intent;
        document.getElementById('ob-toggle-upgrade').classList.toggle('active');
        document.getElementById('ob-toggle-upgrade').setAttribute('aria-checked', data.upgrade_intent);
      });
    }

    if (currentStep === 6) {
      bindTagInput('ob-skills-input', 'skills');
      document.querySelectorAll('#ob-skills-area .tag-remove').forEach(btn => {
        btn.addEventListener('click', () => {
          data.skills = data.skills.filter(t => t !== btn.dataset.tag);
          updateStepUI('forward');
        });
      });
    }

    if (currentStep === 7) {
      bindTagInput('ob-certs-input', 'certificates');
      document.querySelectorAll('#ob-certs-area .tag-remove').forEach(btn => {
        btn.addEventListener('click', () => {
          data.certificates = data.certificates.filter(t => t !== btn.dataset.tag);
          updateStepUI('forward');
        });
      });
    }
  }

  function bindEvents() {
    document.getElementById('ob-btn-next').addEventListener('click', onNext);
    document.getElementById('ob-btn-skip').addEventListener('click', onSkip);
    document.getElementById('ob-btn-back').addEventListener('click', onPrev);
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
          updateStepUI('forward');
        }
      }
    });
  }

  function restoreData() {
    const saved = JSON.parse(localStorage.getItem('ob_profile') || '{}');
    Object.keys(saved).forEach(k => {
      if (k in data) data[k] = saved[k];
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

  function onNext() {
    if (transitioning) return;

    if (currentStep === 1) {
      currentStep = 2;
      updateStepUI('forward');
      return;
    }

    if (currentStep === totalSteps) {
      if (!skipped) {
        autoSave().then(() => {
          localStorage.removeItem('ob_profile');
          window.location.hash = '#/chat';
        });
      } else {
        localStorage.removeItem('ob_profile');
        window.location.hash = '#/chat';
      }
      return;
    }

    if (currentStep > 1 && currentStep < totalSteps) {
      autoSave();
    }
    currentStep++;
    updateStepUI('forward');
  }

  function onPrev() {
    if (transitioning || currentStep <= 1) return;
    currentStep--;
    updateStepUI('backward');
  }

  function onSkip() {
    skipped = true;
    currentStep = totalSteps;
    updateStepUI('forward');
  }

  contentEl.innerHTML = buildShell();
  restoreData();
  bindEvents();
  bindStepEvents();
}

registerRoute('#/onboarding', (o) => {
  initOnboardingPage(o);
});
