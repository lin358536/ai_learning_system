/* ========== 智途校园 — 对话页（SSE流式 + 侧边栏 + 保存规划/简历） ========== */
function initChatPage() {
  const content = document.getElementById('page-content');
  let sidebarVisible = true;

  const conversations = [
    { date: '今天', items: [
      { icon: '💬', title: '关于Python数据分析的讨论', time: '14:32', active: true },
      { icon: '📋', title: '帮我制定学习规划', time: '11:15' },
    ]},
    { date: '昨天', items: [
      { icon: '📄', title: '生成一份数据工程师简历', time: '20:41' },
      { icon: '💬', title: 'SQL优化技巧有哪些', time: '16:08' },
      { icon: '💬', title: '专升本要怎么准备', time: '09:22' },
    ]},
  ];

  function renderSidebar(filter) {
    const val = filter || '';
    let html = `
      <div class="sidebar-header">
        <input class="sidebar-search" id="sidebar-search" value="${val}" placeholder="搜索对话..." autocomplete="off">
        <button class="sidebar-close-btn" id="sidebar-close">✕</button>
      </div>
      <div class="chat-list" id="chat-list">`;

    let hasItems = false;
    conversations.forEach(group => {
      const filtered = filter
        ? group.items.filter(i => i.title.includes(filter))
        : group.items;
      if (!filtered.length) return;
      hasItems = true;

      html += `<div class="chat-date-label">${group.date}</div>`;
      filtered.forEach(item => {
        html += `
          <div class="chat-item${item.active ? ' active' : ''}">
            <div class="chat-item-icon">${item.icon}</div>
            <div class="chat-item-content">
              <div class="chat-item-title">${item.title}</div>
              <div class="chat-item-time">${item.time}</div>
            </div>
          </div>`;
      });
    });

    if (!hasItems) {
      html += '<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;">无匹配对话</div>';
    }

    html += '</div>';
    return html;
  }

  function toggleSidebar(show) {
    sidebarVisible = show !== undefined ? show : !sidebarVisible;
    const layout = document.getElementById('chat-layout');
    layout.classList.toggle('sidebar-collapsed', !sidebarVisible);
  }

  content.innerHTML = `
    <link rel="stylesheet" href="/static/css/chat.css">
    <div class="chat-layout" id="chat-layout">
      <div class="chat-sidebar" id="chat-sidebar">
        ${renderSidebar('')}
      </div>
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

  // 侧边栏事件绑定
  document.getElementById('sidebar-close').addEventListener('click', () => toggleSidebar(false));

  document.getElementById('sidebar-open').addEventListener('click', () => toggleSidebar(true));

  function bindSearch() {
    const searchInput = document.getElementById('sidebar-search');
    if (!searchInput) return;
    searchInput.addEventListener('input', function onSearch() {
      const sidebar = document.getElementById('chat-sidebar');
      const val = searchInput.value.trim();
      sidebar.innerHTML = renderSidebar(val);
      document.getElementById('sidebar-close').addEventListener('click', () => toggleSidebar(false));
      bindSearch();
    });
    // 重新聚焦
    searchInput.focus();
    const len = searchInput.value.length;
    searchInput.setSelectionRange(len, len);
    // 定位光标到末尾
  }
  bindSearch();

  const messagesEl = document.getElementById('chat-messages');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send');
  let isStreaming = false;

  // 欢迎消息
  function showWelcome() {
    messagesEl.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-icon">🎓</div>
        <h3>你好，欢迎使用智途校园</h3>
        <p>我是小途，你的校园成长助手。<br>我可以帮你制定学习规划、生成求职简历、解答学习问题。</p>
      </div>`;
  }

  function appendMessage(role, content, time) {
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
    requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
  }

  // 保存规划/简历到后端（可复用，支持重试）
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

  // 在AI回复后追加操作卡片（保存规划/简历）
  function appendActionCard(intent, fullContent) {
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

    // 绑定保存按钮事件（保存 + 重试都走同一个函数）
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

  // 从用户消息中预判意图（作为后端意图识别的补充）
  function detectUserIntent(msg) {
    if (/规划|计划|路线|路径|方案/.test(msg)) return 'generate_plan';
    if (/简历|求职|cv|resume/i.test(msg)) return 'generate_resume';
    return null;
  }

  // 从AI回复中检测是否有结构化内容（确认AI确实生成了规划/简历）
  function hasStructuredContent(text) {
    if (/阶段|步骤|目标|任务清单/.test(text)) return 'generate_plan';
    if (/教育背景|工作经验|项目经历|专业技能|自我评价/.test(text)) return 'generate_resume';
    return null;
  }

  // 发送消息
  async function sendMessage() {
    const msg = inputEl.value.trim();
    if (!msg || isStreaming) return;

    // 预判用户意图
    const userIntent = detectUserIntent(msg);

    isStreaming = true;
    inputEl.value = '';
    inputEl.disabled = true;
    sendBtn.disabled = true;

    // 清除欢迎消息
    const welcome = messagesEl.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // 显示用户消息
    appendMessage('user', msg);

    // 创建流式消息气泡
    const bubble = appendStreamBubble();
    let fullText = '';

    try {
      const response = await ChatAPI.sendMessage(msg);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let lastIntent = 'chat';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留未完成的行

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
              // 如果AI回复包含完整内容（流式中已拼接），用流中拼接的
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
      // 优先用后端意图，其次用前端预判 + 内容验证
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
      document.getElementById('stream-msg')?.removeAttribute('id');
      document.getElementById('stream-bubble')?.removeAttribute('id');
      document.getElementById('stream-time')?.removeAttribute('id');
    }
  }

  // 事件绑定
  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

  // 显示欢迎消息
  showWelcome();
  inputEl.focus();
}

registerRoute('#/chat', (el) => { initChatPage(); });
registerRoute('#/', (el) => { window.location.hash = '#/chat'; });
registerRoute('', (el) => { window.location.hash = '#/chat'; });
