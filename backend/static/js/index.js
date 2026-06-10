/* ========== 功能总览页 ========== */

function initIndexPage() {
  const content = document.getElementById('page-content');
  if (!content) return;

  const user = getUser();
  const userName = user?.name || '用户';

  const categories = [
    {
      title: '学业与升学规划',
      subtitle: '怎么学、怎么考 — 从日常学习到学历提升',
      features: [
        {
          name: '学习规划',
          desc: 'AI 定制学习计划，任务管理',
          route: '#/plans',
          status: 'live',
          icon: 'checklist'
        },
        {
          name: '升本方案规划',
          desc: '个性化升本备考方案',
          route: null,
          status: 'coming',
          icon: 'rocket'
        }
      ]
    },
    {
      title: '职业发展与就业',
      subtitle: '我是谁、要去哪 — 从职业探索到求职落地',
      features: [
        {
          name: '职业能力测评',
          desc: '能力雷达图 + 积分 + 排行榜',
          route: '#/learn',
          status: 'live',
          icon: 'radar'
        },
        {
          name: '简历制作',
          desc: '智能生成求职简历',
          route: '#/resumes',
          status: 'live',
          icon: 'document'
        },
        {
          name: '职业兴趣测试',
          desc: '科学测评职业倾向',
          route: null,
          status: 'coming',
          icon: 'target'
        },
      ]
    },
    {
      title: '社交成长与心理支持',
      subtitle: '心理健康与软实力 — 构建积极校园圈子',
      features: [
        {
          name: 'AI 聊天',
          desc: '智能对话，学习辅导与答疑',
          route: '#/chat',
          status: 'live',
          icon: 'chat'
        }
      ]
    }
  ];

  content.innerHTML = `
    <div class="feature-page">
      <div class="feature-header">
        <p class="feature-subtitle">欢迎, ${userName} — 探索智途校园全部功能</p>
      </div>

      ${categories.map(cat => {
        const liveCount = cat.features.filter(f => f.status === 'live').length;
        const comingCount = cat.features.filter(f => f.status === 'coming').length;
        const countLabel = liveCount > 0 && comingCount > 0
          ? `${liveCount} 个已上线 · ${comingCount} 个即将推出`
          : liveCount > 0 ? `${liveCount} 个功能` : `${comingCount} 个即将推出`;
        return `
          <div class="feature-section">
            <h2 class="feature-section-title">${cat.title}</h2>
            <div class="feature-grid">
              ${cat.features.map(f => renderFeatureCard(f)).join('')}
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;

  // 绑定已上线卡片点击事件
  content.querySelectorAll('.feature-card:not(.coming-soon)').forEach(card => {
    card.addEventListener('click', () => {
      const route = card.dataset.route;
      if (route) window.location.hash = route;
    });
  });
}

function renderFeatureCard(feature) {
  const isComing = feature.status === 'coming';
  const cardClass = `feature-card${isComing ? ' coming-soon' : ''}`;

  return `
    <div class="${cardClass}" data-route="${feature.route || ''}" ${isComing ? '' : 'tabindex="0"'}>
      <div class="feature-card-header">
        <div class="feature-icon">${getFeatureIcon(feature.icon, isComing)}</div>
        <h3 class="feature-name">${feature.name}</h3>
        ${isComing
          ? '<span class="feature-badge">即将推出</span>'
          : '<span class="feature-link">进入 →</span>'
        }
      </div>
      <p class="feature-desc">${feature.desc}</p>
    </div>
  `;
}

function getFeatureIcon(type, disabled) {
  const stroke = disabled ? 'var(--text-disabled)' : 'var(--primary)';
  const fillAccent = disabled ? 'var(--text-disabled)' : 'var(--primary)';
  
  // 统一使用 1.5 线宽，更符合 Apple HIG 的精致感
  const attrs = `stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"`;
  
  const icons = {
    radar: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <polygon points="12 2 20.7 7 20.7 17 12 22 3.3 17 3.3 7" />
      <line x1="12" y1="2" x2="12" y2="22" />
      <line x1="3.3" y1="7" x2="20.7" y2="17" />
      <line x1="20.7" y1="7" x2="3.3" y2="17" />
      <polygon points="12 6 17 9.5 16 15 8 14 6 9" fill="${fillAccent}" fill-opacity="0.15" stroke="${stroke}" />
    </svg>`,
    
    checklist: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <line x1="11" y1="7" x2="20" y2="7" />
      <line x1="11" y1="12" x2="20" y2="12" />
      <line x1="11" y1="17" x2="20" y2="17" />
      <polyline points="4 7 5.5 8.5 8 5.5" />
      <polyline points="4 12 5.5 13.5 8 10.5" />
      <polyline points="4 17 5.5 18.5 8 15.5" />
    </svg>`,
    
    document: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <rect x="4" y="2" width="16" height="20" rx="2.5" />
      <circle cx="12" cy="7.5" r="2.5" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="8" y1="16.5" x2="16" y2="16.5" />
      <line x1="10" y1="20" x2="14" y2="20" />
    </svg>`,
    
    target: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
      <line x1="12" y1="2" x2="12" y2="4" />
      <line x1="12" y1="20" x2="12" y2="22" />
      <line x1="2" y1="12" x2="4" y2="12" />
      <line x1="20" y1="12" x2="22" y2="12" />
    </svg>`,
    
    rocket: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <path d="M12 2C8.5 6 7 11 7 15h10c0-4-1.5-9-5-13z" />
      <path d="M7 15l-2 3h14l-2-3" />
      <circle cx="12" cy="10" r="2" />
      <path d="M10 18v3" />
      <path d="M14 18v3" />
      <path d="M12 18v4" />
    </svg>`,

    chat: `<svg viewBox="0 0 24 24" width="24" height="24" ${attrs}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <line x1="8" y1="9" x2="16" y2="9" />
      <line x1="8" y1="13" x2="12" y2="13" />
    </svg>`
  };
  
  return icons[type] || '';
}

registerRoute('#/index', (el) => { initIndexPage(); });
