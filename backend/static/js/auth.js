/* ========== 智途校园 — 登录/注册页 ========== */
function initLoginPage() {
  let isRegister = false;

  function render() {
    const app = document.getElementById('app');
    app.innerHTML = `
      <div class="login-wrapper">
        <div class="login-box">
          <div class="login-logo">
            <div class="logo-circle">
              <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z" fill="#fff"/></svg>
            </div>
          </div>
          <div class="login-title">智途校园</div>
          <div class="login-subtitle">大学生 AI 成长服务平台</div>
          <div class="login-error" id="login-error"></div>
          <div class="login-form" id="login-form">
            ${isRegister ? `
              <div class="form-group">
                <label class="form-label">用户名</label>
                <input class="form-input" id="inp-username" type="text" placeholder="请输入用户名（3位以上）" autocomplete="username">
              </div>
              <div class="form-group">
                <label class="form-label">姓名（选填）</label>
                <input class="form-input" id="inp-name" type="text" placeholder="你的真实姓名">
              </div>
              <div class="form-group">
                <label class="form-label">邮箱（选填）</label>
                <input class="form-input" id="inp-email" type="email" placeholder="your@email.com">
              </div>
            ` : `
              <div class="form-group">
                <label class="form-label">用户名 / 邮箱</label>
                <input class="form-input" id="inp-username" type="text" placeholder="请输入用户名" autocomplete="username" autofocus>
              </div>
            `}
            <div class="form-group">
              <label class="form-label">密码</label>
              <input class="form-input" id="inp-password" type="password" placeholder="请输入密码" autocomplete="${isRegister ? 'new-password' : 'current-password'}">
            </div>
            ${isRegister ? `
              <div class="form-group">
                <label class="form-label">确认密码</label>
                <input class="form-input" id="inp-password2" type="password" placeholder="再次输入密码" autocomplete="new-password">
              </div>
            ` : ''}
            <div class="login-actions">
              <button class="btn btn-primary" id="btn-submit">${isRegister ? '注册' : '登录'}</button>
              <button class="btn btn-outline" id="btn-switch">${isRegister ? '去登录' : '注册'}</button>
            </div>
          </div>
          <div class="login-switch">${isRegister ? '已有账号？<a id="link-switch">去登录</a>' : '还没有账号？<a id="link-switch">去注册</a>'}</div>
        </div>
      </div>`;

    // 自动聚焦
    setTimeout(() => document.getElementById('inp-username')?.focus(), 100);

    // 事件绑定
    document.getElementById('btn-submit').addEventListener('click', handleSubmit);
    document.getElementById('btn-switch').addEventListener('click', () => { isRegister = !isRegister; render(); });
    document.getElementById('link-switch').addEventListener('click', () => { isRegister = !isRegister; render(); });
    document.getElementById('inp-password')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleSubmit(); });
  }

  async function handleSubmit() {
    const username = document.getElementById('inp-username').value.trim();
    const password = document.getElementById('inp-password').value;
    const errEl = document.getElementById('login-error');

    if (!username || !password) { errEl.textContent = '请填写用户名和密码'; errEl.style.display = 'block'; return; }
    if (isRegister && password.length < 6) { errEl.textContent = '密码至少6位'; errEl.style.display = 'block'; return; }
    if (isRegister && password !== document.getElementById('inp-password2').value) { errEl.textContent = '两次密码不一致'; errEl.style.display = 'block'; return; }

    const btn = document.getElementById('btn-submit');
    btn.disabled = true;
    errEl.style.display = 'none';

    try {
      let result;
      if (isRegister) {
        const email = document.getElementById('inp-email').value.trim() || null;
        const name = document.getElementById('inp-name').value.trim() || null;
        result = await AuthAPI.register({ username, password, email, name });
      } else {
        result = await AuthAPI.login(username, password);
      }

      if (result.success && result.data) {
        setToken(result.data.token);
        setUser(result.data.user);
        window.location.hash = isRegister ? '#/onboarding' : '#/chat';
      } else {
        errEl.textContent = result.error?.message || '操作失败';
        errEl.style.display = 'block';
      }
    } catch (e) {
      errEl.textContent = e.message;
      errEl.style.display = 'block';
    } finally {
      btn.disabled = false;
    }
  }

  render();
}

registerRoute('#/login', (el) => {
  initLoginPage();
});
