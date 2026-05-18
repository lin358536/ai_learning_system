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
  async getHistory(conversationId = null, page = 1, limit = 50) {
    let url = `/chat/history?page=${page}&limit=${limit}`;
    if (conversationId) url += `&conversation_id=${conversationId}`;
    return request(url);
  }
};

// ========== 个人画像 ==========
const ProfileAPI = {
  async get() { return request('/profile'); },
  async update(data) { return request('/profile', { method: 'PUT', body: JSON.stringify(data) }); }
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
