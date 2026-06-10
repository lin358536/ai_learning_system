/* ========== 智途校园 — API 封装 ========== */

const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('zhitu_token');
}

function setToken(token) {
  localStorage.setItem('zhitu_token', token);
}

function removeToken() {
  localStorage.removeItem('zhitu_token');
  localStorage.removeItem('zhitu_user');
}

function setUser(user) {
  localStorage.setItem('zhitu_user', JSON.stringify(user));
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('zhitu_user'));
  } catch { return null; }
}

async function request(url, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (res.status === 401) {
    removeToken();
    window.location.hash = '#/login';
    throw new Error('登录已过期，请重新登录');
  }

  if (!res.ok) {
    let errMsg = '请求失败';
    try {
      const errBody = await res.json();
      errMsg = errBody?.detail?.error?.message || errBody?.error?.message || errMsg;
    } catch {}
    throw new Error(errMsg);
  }

  // SSE 不解析 JSON
  if (res.headers.get('content-type')?.includes('text/event-stream')) {
    return res;
  }

  return res.json();
}

// ========== 认证 ==========
const AuthAPI = {
  async register(data) {
    return request('/auth/register', { method: 'POST', body: JSON.stringify(data) });
  },
  async login(username, password) {
    return request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
  },
  async getMe() {
    return request('/auth/me');
  }
};

// ========== 对话 ==========
const ChatAPI = {
  async sendMessage(message, conversationId = null) {
    const token = getToken();
    const body = { message };
    if (conversationId) body.conversation_id = conversationId;
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(body)
    });
    if (res.status === 401) { removeToken(); window.location.hash = '#/login'; throw new Error('登录已过期'); }
    if (!res.ok) throw new Error('发送失败');
    return res; // 返回 Response 对象用于 SSE 读取
  },
  async confirm(confirmId, action) {
    return request('/chat/confirm', { method: 'POST', body: JSON.stringify({ confirm_id: confirmId, action }) });
  },
  // 获取对话列表（按 conversation_id 分组）
  async getConversations(page = 1, limit = 50) {
    return request(`/chat/conversations?page=${page}&limit=${limit}`);
  },
  // 获取指定对话的所有消息
  async getConversationMessages(conversationId) {
    return request(`/chat/conversations/${conversationId}`);
  },
  // 删除指定对话
  async deleteConversation(conversationId) {
    return request(`/chat/conversations/${conversationId}`, { method: 'DELETE' });
  },
  // 清空全部历史
  async clearHistory() {
    return request('/chat/history', { method: 'DELETE' });
  }
};

// ========== 个人画像 ==========
const ProfileAPI = {
  async get() { return request('/profile'); },
  async update(data) { return request('/profile', { method: 'PUT', body: JSON.stringify(data) }); },
  async updateBasic(data) { return request('/profile/basic', { method: 'PUT', body: JSON.stringify(data) }); },
  async uploadAvatar(file) {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/profile/avatar`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    if (res.status === 401) { removeToken(); window.location.hash = '#/login'; throw new Error('登录已过期'); }
    if (!res.ok) {
      let errMsg = '上传失败';
      try { const b = await res.json(); errMsg = b?.detail?.error?.message || b?.error?.message || errMsg; } catch {}
      throw new Error(errMsg);
    }
    return res.json();
  }
};

// ========== 学习规划 ==========
const PlanAPI = {
  async list() { return request('/plans'); },
  async getDetail(id) { return request(`/plans/${id}`); },
  async delete(id) { return request(`/plans/${id}`, { method: 'DELETE' }); },
  async toggleTask(planId, taskId, completed) {
    return request(`/plans/${planId}/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify({ completed })
    });
  }
};

// ========== 简历 ==========
const ResumeAPI = {
  async list() { return request('/resumes'); },
  async getDetail(id) { return request(`/resumes/${id}`); },
  async delete(id) { return request(`/resumes/${id}`, { method: 'DELETE' }); }
};

// ========== 积分 ==========
const PointsAPI = {
  async get() { return request('/points'); },
  async getRank(limit = 10) { return request(`/points/rank?limit=${limit}`); }
};

// ========== 能力维度 ==========
const AbilitiesAPI = {
  async get() { return request('/abilities'); }
};
