/* ========== 智途校园 — 对话页（SSE流式 + 真实对话列表 + 保存规划/简历） ========== */
let currentConversationId = null;   // 当前活跃对话 ID（null 表示新对话）
let sidebarVisible = true;          // 侧边栏是否可见
let isStreaming = false;            // 是否正在流式回复
let conversations = [];             // 对话列表数据

// 生成 UUID v4
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function initChatPage() {
  const content = document.getElementById('page-content');

  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/chat.css">
    <div class="chat-layout" id="chat-layout">
      <div class="chat-sidebar" id="chat-sidebar"></div>
      <div class="chat-main">
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-area">
          <button class="sidebar-open-btn" id="sidebar-open" title="展开会话列表">☰</button>
          <input class="chat-input" id="chat-input" placeholder="输入消息，和小途对话..." maxlength="1000" autocomplete="off">
          <button class="chat-send" id="btn-send">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>
    </div>`;

  // 初始化状态
  currentConversationId = null;
  sidebarVisible = true;
  isStreaming = false;
  conversations = [];

  // 加载对话列表 & 显示欢迎页
  loadConversations().then(() => {
    renderSidebar();
    showWelcome();
  });

  // 事件绑定
  bindEvents();
}

// ── 加载对话列表 ──────────────────────────────────────────────
async function loadConversations() {
  try {
    const res = await ChatAPI.getConversations(1, 100);
    if (res.success) {
      conversations = res.data.conversations || [];
    }
  } catch (e) {
    console.error('加载对话列表失败:', e);
    conversations = [];
  }
}

// ── 侧边栏渲染 ──────────────────────────────────────────────
function renderSidebar(filter) {
  const sidebar = document.getElementById('chat-sidebar');
  const val = (filter || '').trim();

  let filtered = conversations;
  if (val) {
    filtered = conversations.filter(c => c.title.includes(val));
  }

  // 按日期分组
  const groups = groupConversationsByDate(filtered);

  let html = `
    <div class="sidebar-header">
      <div style="flex:1;font-size:13px;font-weight:600;color:var(--text-primary);">对话历史</div>
      <button class="sidebar-new-btn" id="btn-new-chat" title="新对话">✚</button>
      <button class="sidebar-close-btn" id="sidebar-close">✕</button>
    </div>
    <div class="sidebar-search-wrap">
      <svg class="search-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input class="sidebar-search" id="sidebar-search" value="${val}" placeholder="搜索对话..." autocomplete="off">
    </div>
    <div class="chat-list" id="chat-list">`;

  if (filtered.length === 0) {
    html += '<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;">' +
      (val ? '无匹配对话' : '暂无对话记录') + '</div>';
  } else {
    for (const group of groups) {
      html += `<div class="chat-date-label">${group.label}</div>`;
      for (const item of group.items) {
        const isActive = item.conversation_id === currentConversationId;
        html += `
          <div class="chat-item${isActive ? ' active' : ''}" data-conv-id="${item.conversation_id}">
            <div class="chat-item-icon">${item.icon || '💬'}</div>
            <div class="chat-item-content">
              <div class="chat-item-title">${item.title || '新对话'}</div>
              <div class="chat-item-meta">
                <span class="chat-item-time">${formatRelativeTime(item.last_message_at)}</span>
                <span class="chat-item-count">${item.message_count} 条</span>
              </div>
            </div>
            <button class="chat-item-delete" data-conv-id="${item.conversation_id}" title="删除对话">✕</button>
          </div>`;
      }
    }
  }

  html += '</div>';
  sidebar.innerHTML = html;

  // 绑定侧边栏事件
  bindSidebarEvents();
}

// ── 按日期分组 ──────────────────────────────────────────────
function groupConversationsByDate(list) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const thisWeek = new Date(today.getTime() - today.getDay() * 86400000);

  const groups = { '今天': [], '昨天': [], '本周': [], '更早': [] };

  for (const item of list) {
    if (!item.last_message_at) {
      groups['更早'].push(item);
      continue;
    }
    const d = new Date(item.last_message_at);
    if (d >= today) groups['今天'].push(item);
    else if (d >= yesterday) groups['昨天'].push(item);
    else if (d >= thisWeek) groups['本周'].push(item);
    else groups['更早'].push(item);
  }

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}

// ── 格式化相对时间 ──────────────────────────────────────────
function formatRelativeTime(dateStr) {
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
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

// ── 绑定侧边栏事件 ──────────────────────────────────────────
function bindSidebarEvents() {
  // 关闭侧边栏
  document.getElementById('sidebar-close')?.addEventListener('click', () => toggleSidebar(false));

  // 新对话
  document.getElementById('btn-new-chat')?.addEventListener('click', startNewConversation);

  // 搜索
  const searchInput = document.getElementById('sidebar-search');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      renderSidebar(this.value);
      // 重新聚焦搜索框
      const newInput = document.getElementById('sidebar-search');
      if (newInput) {
        newInput.focus();
        newInput.setSelectionRange(newInput.value.length, newInput.value.length);
      }
    });
    setTimeout(() => searchInput.focus(), 50);
  }

  // 点击对话项 → 加载对话
  document.querySelectorAll('.chat-item').forEach(el => {
    el.addEventListener('click', (e) => {
      // 如果点击的是删除按钮，不触发加载
      if (e.target.closest('.chat-item-delete')) return;
      const convId = el.dataset.convId;
      if (convId && convId !== currentConversationId) {
        loadConversationMessages(convId);
      }
    });
  });

  // 删除对话
  document.querySelectorAll('.chat-item-delete').forEach(el => {
    el.addEventListener('click', async (e) => {
      e.stopPropagation();
      const convId = el.dataset.convId;
      const confirmed = await showConfirm('确定要删除此对话？');
      if (confirmed) {
        await deleteConversation(convId);
      }
    });
  });
}

// ── 加载对话消息 ────────────────────────────────────────────
async function loadConversationMessages(convId) {
  try {
    const res = await ChatAPI.getConversationMessages(convId);
    if (!res.success) {
      showToast('加载对话失败', 'error');
      return;
    }

    currentConversationId = convId;
    const messages = res.data.messages || [];

    // 清空消息区
    const messagesEl = document.getElementById('chat-messages');
    messagesEl.innerHTML = '';

    // 渲染消息
    for (const msg of messages) {
      if (msg.role === 'user') {
        appendMessage('user', msg.content, msg.created_at);
      } else if (msg.role === 'assistant') {
        appendMessage('assistant', msg.content, msg.created_at);
      }
    }

    // 更新侧边栏高亮
    renderSidebar(document.getElementById('sidebar-search')?.value || '');
    toggleSidebar(false); // 移动端自动收起侧边栏
  } catch (e) {
    showToast('加载对话失败: ' + e.message, 'error');
  }
}

// ── 新对话 ──────────────────────────────────────────────────
function startNewConversation() {
  currentConversationId = null;
  const messagesEl = document.getElementById('chat-messages');
  messagesEl.innerHTML = '';
  showWelcome();

  // 清除输入框
  const inputEl = document.getElementById('chat-input');
  if (inputEl) inputEl.value = '';

  // 更新侧边栏高亮
  renderSidebar(document.getElementById('sidebar-search')?.value || '');
  toggleSidebar(false);
}

// ── 删除对话 ────────────────────────────────────────────────
async function deleteConversation(convId) {
  try {
    const res = await ChatAPI.deleteConversation(convId);
    if (res.success) {
      showToast('对话已删除', 'success');
      // 如果删除的是当前对话，回到新对话状态
      if (convId === currentConversationId) {
        startNewConversation();
      } else {
        await loadConversations();
        renderSidebar(document.getElementById('sidebar-search')?.value || '');
      }
    }
  } catch (e) {
    showToast('删除失败: ' + e.message, 'error');
  }
}

// ── 切换侧边栏 ──────────────────────────────────────────────
function toggleSidebar(show) {
  sidebarVisible = show !== undefined ? show : !sidebarVisible;
  const layout = document.getElementById('chat-layout');
  if (layout) layout.classList.toggle('sidebar-collapsed', !sidebarVisible);
}

// ── 绑定主区事件 ────────────────────────────────────────────
function bindEvents() {
  document.getElementById('sidebar-open')?.addEventListener('click', () => toggleSidebar(true));

  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send');

  sendBtn?.addEventListener('click', sendMessage);
  inputEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

// ── 欢迎消息 ────────────────────────────────────────────────
function showWelcome() {
  const messagesEl = document.getElementById('chat-messages');
  if (!messagesEl) return;
  messagesEl.innerHTML = `
    <div class="welcome-message">
      <div class="welcome-icon">🎓</div>
      <h3>你好，欢迎使用智途校园</h3>
      <p>我是小途，你的校园成长助手。<br>我可以帮你制定学习规划、生成求职简历、解答学习问题。</p>
    </div>`;
}

// ── 追加消息气泡 ────────────────────────────────────────────
function appendMessage(role, content, time) {
  const messagesEl = document.getElementById('chat-messages');
  if (!messagesEl) return;
  const isUser = role === 'user';
  const user = getUser();
  const avatar = isUser ? (user?.name?.[0] || '你') : '途';
  const avatarClass = isUser ? 'msg-user' : 'msg-ai';
  const html = content.startsWith('[') ? content : renderMarkdown(content);
  const timeStr = time ? formatDate(time) : '';
  messagesEl.innerHTML += `
    <div class="msg ${avatarClass}">
      <div class="msg-avatar">${avatar}</div>
      <div>
        <div class="msg-bubble">${html}</div>
        <div class="msg-time">${timeStr}</div>
      </div>
    </div>`;
  scrollToBottom();
}

function appendStreamBubble() {
  const messagesEl = document.getElementById('chat-messages');
  const html = `
    <div class="msg msg-ai" id="stream-msg">
      <div class="msg-avatar">途</div>
      <div>
        <div class="msg-bubble" id="stream-bubble"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>
        <div class="msg-time" id="stream-time">刚刚</div>
      </div>
    </div>`;
  messagesEl.innerHTML += html;
  scrollToBottom();
  return document.getElementById('stream-bubble');
}

function scrollToBottom() {
  const messagesEl = document.getElementById('chat-messages');
  if (messagesEl) requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
}

// ── 保存规划/简历 ──────────────────────────────────────────
async function saveContent(intent, fullContent) {
  const url = intent === 'generate_plan' ? '/chat/save-plan' : '/chat/save-resume';
  const label = intent === 'generate_plan' ? '规划' : '简历';
  const btnId = intent === 'generate_plan' ? 'btn-save-plan' : 'btn-save-resume';
  const card = document.getElementById(btnId)?.closest('.action-card');
  if (card) card.querySelector('.action-card-actions').innerHTML = '<div class="spinner"></div>';

  try {
    const res = await request(url, {
      method: 'POST',
      body: JSON.stringify({ content: fullContent })
    });
    if (res.success) {
      showToast(`${label}已保存，可在「${label}」页面查看`, 'success');
      if (card) card.innerHTML = `<div style="color:var(--primary);font-size:13px;padding:4px 0;">✓ ${label}已保存</div>`;
    } else {
      showToast(res.error?.message || '保存失败', 'error');
      if (card) card.querySelector('.action-card-actions').innerHTML = `<button class="btn btn-primary btn-sm" id="${btnId}">✓ 重试保存</button>`;
      document.getElementById(btnId)?.addEventListener('click', () => saveContent(intent, fullContent));
    }
  } catch (e) {
    showToast(e.message || '网络异常', 'error');
    if (card) card.querySelector('.action-card-actions').innerHTML = `<button class="btn btn-primary btn-sm" id="${btnId}">✓ 重试保存</button>`;
    document.getElementById(btnId)?.addEventListener('click', () => saveContent(intent, fullContent));
  }
}

function appendActionCard(intent, fullContent) {
  const messagesEl = document.getElementById('chat-messages');
  let cardHtml = '';
  if (intent === 'generate_plan') {
    cardHtml = `
      <div class="msg msg-ai">
        <div class="msg-avatar">途</div>
        <div>
          <div class="action-card">
            <div class="action-card-title">📋 检测到学习规划</div>
            <div class="action-card-body">小途为你生成了学习规划内容，是否保存到「我的规划」？</div>
            <div class="action-card-actions">
              <button class="btn btn-primary btn-sm" id="btn-save-plan">✓ 保存规划</button>
              <button class="btn btn-ghost btn-sm" id="btn-skip-plan">跳过</button>
            </div>
          </div>
        </div>
      </div>`;
  } else if (intent === 'generate_resume') {
    cardHtml = `
      <div class="msg msg-ai">
        <div class="msg-avatar">途</div>
        <div>
          <div class="action-card">
            <div class="action-card-title">📄 检测到简历</div>
            <div class="action-card-body">小途为你生成了简历内容，是否保存到「我的简历」？</div>
            <div class="action-card-actions">
              <button class="btn btn-primary btn-sm" id="btn-save-resume">✓ 保存简历</button>
              <button class="btn btn-ghost btn-sm" id="btn-skip-resume">跳过</button>
            </div>
          </div>
        </div>
      </div>`;
  }

  if (!cardHtml) return;
  messagesEl.innerHTML += cardHtml;
  scrollToBottom();

  if (intent === 'generate_plan') {
    document.getElementById('btn-save-plan')?.addEventListener('click', () => saveContent(intent, fullContent));
    document.getElementById('btn-skip-plan')?.addEventListener('click', () => {
      document.getElementById('btn-skip-plan')?.closest('.action-card').remove();
    });
  } else if (intent === 'generate_resume') {
    document.getElementById('btn-save-resume')?.addEventListener('click', () => saveContent(intent, fullContent));
    document.getElementById('btn-skip-resume')?.addEventListener('click', () => {
      document.getElementById('btn-skip-resume')?.closest('.action-card').remove();
    });
  }
}

// ── 意图检测 ────────────────────────────────────────────────
function detectUserIntent(msg) {
  if (/规划|计划|路线|路径|方案/.test(msg)) return 'generate_plan';
  if (/简历|求职|cv|resume/i.test(msg)) return 'generate_resume';
  return null;
}

function hasStructuredContent(text) {
  if (/阶段|步骤|目标|任务清单/.test(text)) return 'generate_plan';
  if (/教育背景|工作经验|项目经历|专业技能|自我评价/.test(text)) return 'generate_resume';
  return null;
}

// ── 发送消息 ────────────────────────────────────────────────
async function sendMessage() {
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send');
  const messagesEl = document.getElementById('chat-messages');
  const msg = inputEl.value.trim();
  if (!msg || isStreaming) return;

  // 预判用户意图
  const userIntent = detectUserIntent(msg);

  isStreaming = true;
  inputEl.value = '';
  inputEl.disabled = true;
  sendBtn.disabled = true;

  // 如果是新对话，生成 conversation_id
  if (!currentConversationId) {
    currentConversationId = generateUUID();
  }

  // 清除欢迎消息
  const welcome = messagesEl.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  // 显示用户消息
  appendMessage('user', msg);

  // 创建流式消息气泡
  const bubble = appendStreamBubble();
  let fullText = '';
  let convIdCaptured = currentConversationId;

  try {
    const response = await ChatAPI.sendMessage(msg, currentConversationId);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let lastIntent = 'chat';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const jsonStr = line.substring(6).trim();
        if (!jsonStr) continue;

        try {
          const event = JSON.parse(jsonStr);
          if (event.type === 'text') {
            fullText += event.content || '';
            bubble.innerHTML = renderMarkdown(fullText);
            scrollToBottom();
          } else if (event.type === 'done') {
            lastIntent = event.intent || 'chat';
            // 捕获后端返回的 conversation_id
            if (event.conversation_id) {
              convIdCaptured = event.conversation_id;
              currentConversationId = event.conversation_id;
            }
            if (event.full_content && !fullText) {
              fullText = event.full_content;
            }
          } else if (event.type === 'error') {
            bubble.innerHTML = `<span style="color:var(--danger);">错误：${event.message || 'AI服务异常'}</span>`;
          }
        } catch (parseErr) {
          // 忽略解析错误
        }
      }
    }

    // 流结束后，根据意图显示操作卡片
    let finalIntent = lastIntent;
    if (finalIntent === 'chat' && userIntent) {
      const contentIntent = hasStructuredContent(fullText);
      if (contentIntent === userIntent) {
        finalIntent = userIntent;
      }
    }
    if (finalIntent === 'generate_plan' || finalIntent === 'generate_resume') {
      appendActionCard(finalIntent, fullText);
    }
  } catch (e) {
    if (fullText) {
      bubble.innerHTML = renderMarkdown(fullText) + `<br><span style="color:var(--danger);font-size:12px;">[连接中断]</span>`;
    } else {
      bubble.innerHTML = `<span style="color:var(--danger);">发送失败：${e.message}</span>`;
    }
  } finally {
    isStreaming = false;
    inputEl.disabled = false;
    sendBtn.disabled = false;
    inputEl.focus();

    // 移除 stream-msg id
    const streamMsg = document.getElementById('stream-msg');
    if (streamMsg) streamMsg.removeAttribute('id');
    const streamBubble = document.getElementById('stream-bubble');
    if (streamBubble) streamBubble.removeAttribute('id');
    const streamTime = document.getElementById('stream-time');
    if (streamTime) streamTime.removeAttribute('id');

    // 更新侧边栏对话列表
    await loadConversations();
    renderSidebar(document.getElementById('sidebar-search')?.value || '');
  }
}

// ── 路由注册 ────────────────────────────────────────────────
registerRoute('#/chat', (el) => { initChatPage(); });
registerRoute('#/', (el) => { window.location.hash = '#/chat'; });
registerRoute('', (el) => { window.location.hash = '#/chat'; });
