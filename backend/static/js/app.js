/* ========== 智途校园 — SPA 路由 + 页面切换 + 工具函数 ========== */

// Toast 通知
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// 简单 Markdown → HTML
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 标题
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 加粗
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 无序列表
    .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
    // 有序列表
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // 引用
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // 换行
    .replace(/\n/g, '<br>');
  // 包裹连续的 li
  html = html.replace(/(<li>.*?<\/li>)+/gs, (match) => `<ul>${match}</ul>`);
  // 清理 br 在 pre 和 blockquote 内
  html = html.replace(/<pre>(.*?)<\/pre>/gs, (m, code) => `<pre>${code.replace(/<br>/g, '\n')}</pre>`);
  return html;
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}天前`;
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function formatDateShort(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

// 确认弹窗
function showConfirm(message) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal" style="width:400px;">
        <div class="modal-body">
          <div class="confirm-dialog">
            <div class="confirm-text">${message}</div>
            <div class="confirm-actions">
              <button class="btn btn-danger-text" id="confirm-cancel">取消</button>
              <button class="btn btn-primary" id="confirm-ok">确定</button>
            </div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('#confirm-ok').onclick = () => { overlay.remove(); resolve(true); };
    overlay.querySelector('#confirm-cancel').onclick = () => { overlay.remove(); resolve(false); };
    overlay.addEventListener('click', (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } });
  });
}

// 渲染导航栏
function renderNavbar() {
  const user = getUser();
  const initial = user?.name ? user.name[0] : '?';
  return `
    <nav class="navbar">
      <div class="nav-logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#fff" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
        </div>
        智途校园
      </div>
      <button class="sidebar-toggle" id="sidebar-toggle"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>
      <div class="nav-links">
        <a class="nav-link" data-page="index" href="#/index">首页</a>
        <a class="nav-link" data-page="learn" href="#/learn">学习</a>
        <a class="nav-link" data-page="plans" href="#/plans">规划</a>
        <a class="nav-link" data-page="resumes" href="#/resumes">简历</a>
        <a class="nav-link" data-page="chat" href="#/chat">聊天</a>
        <a class="nav-link" data-page="profile" href="#/profile">我的</a>
      </div>
      <div class="nav-right">
        <div class="nav-avatar" title="${user?.name || '未登录'}">${initial}</div>
      </div>
    </nav>
    <div class="toast-container" id="toast-container"></div>`;
}

// ========== 路由 ==========
const routes = {};

function registerRoute(path, handler) {
  routes[path] = handler;
}

function navigateTo(hash) {
  window.location.hash = hash;
}

function getCurrentRoute() {
  const hash = window.location.hash || '#/';
  return hash;
}

function matchRoute(hash) {
  // 精确匹配
  if (routes[hash]) return { handler: routes[hash], params: {} };
  // 参数匹配 如 #/plans/1
  for (const [pattern, handler] of Object.entries(routes)) {
    const regex = new RegExp('^' + pattern.replace(/:\w+/g, '([\\w-]+)') + '$');
    const match = hash.match(regex);
    if (match) {
      const paramNames = [...pattern.matchAll(/:(\w+)/g)].map(m => m[1]);
      const params = {};
      paramNames.forEach((name, i) => params[name] = match[i + 1]);
      return { handler, params };
    }
  }
  return null;
}

function handleRoute() {
  const hash = getCurrentRoute();
  const result = matchRoute(hash);

  // 检查是否需要登录
  if (hash !== '#/login' && hash !== '#/onboarding') {
    if (!getToken()) { navigateTo('#/login'); return; }
  }

    // 清空页面（登录页/引导页不需要导航）
    const app = document.getElementById('app');
    if (hash === '#/login' || hash === '#/onboarding') {
      app.innerHTML = '';
    } else {
      app.innerHTML = renderNavbar();
      // 更新导航高亮
      const page = hash.split('/')[1] || 'index';
      document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === page);
      });
    }

  const fullPageRoutes = ['#/login', '#/onboarding'];
  const contentEl = fullPageRoutes.includes(hash) ? app : document.createElement('div');
  if (!fullPageRoutes.includes(hash)) {
    contentEl.id = 'page-content';
    contentEl.className = 'page-content';
    app.appendChild(contentEl);
  }

  if (result) {
    result.handler(contentEl, result.params);
  } else {
    contentEl.innerHTML = '<div class="empty-state"><div class="empty-icon"><svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div><div class="empty-text">页面不存在</div></div>';
  }
}

// 初始化路由
window.addEventListener('hashchange', handleRoute);
window.addEventListener('DOMContentLoaded', handleRoute);
