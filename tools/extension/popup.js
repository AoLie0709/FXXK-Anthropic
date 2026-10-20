/**
 * Claude 隐私护盾 - Popup 交互控制器
 */

document.addEventListener('DOMContentLoaded', () => {
  // 元素引用
  const cardAuto = document.getElementById('cardAuto');
  const cardTaiwan = document.getElementById('cardTaiwan');
  const cardUS = document.getElementById('cardUS');
  const radios = document.querySelectorAll('input[name="mode"]');
  
  const nodeFlag = document.getElementById('nodeFlag');
  const nodeLocation = document.getElementById('nodeLocation');
  const nodeIp = document.getElementById('nodeIp');
  const nodeTimezone = document.getElementById('nodeTimezone');
  const nodeLang = document.getElementById('nodeLang');
  const nodeIsp = document.getElementById('nodeIsp');
  const syncStatus = document.getElementById('syncStatus');
  const btnRefreshNode = document.getElementById('btnRefreshNode');

  const btnOpenClaude = document.getElementById('btnOpenClaude');
  const btnTestYouClaude = document.getElementById('btnTestYouClaude');
  const btnTestBewild = document.getElementById('btnTestBewild');
  const btnTestLeak = document.getElementById('btnTestLeak');
  const btnTestIp = document.getElementById('btnTestIp');
  const extVersion = document.getElementById('extVersion');
  if (extVersion && chrome.runtime && chrome.runtime.getManifest) {
    extVersion.textContent = `v${chrome.runtime.getManifest().version}`;
  }

  // 账号状态与封禁诊断台元素引用
  const standingBadge = document.getElementById('standingBadge');
  const btnCheckStanding = document.getElementById('btnCheckStanding');
  const stStanding = document.getElementById('stStanding');
  const stBanReason = document.getElementById('stBanReason');
  const stBannedAtTier = document.getElementById('stBannedAtTier');
  const stBannedOrgs = document.getElementById('stBannedOrgs');
  const stAppealStatus = document.getElementById('stAppealStatus');
  const stExportBilling = document.getElementById('stExportBilling');

  function formatLocalTime(isoStr) {
    if (!isoStr) return null;
    try {
      const d = new Date(isoStr);
      if (Number.isNaN(d.getTime())) return isoStr;
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    } catch (e) {
      return isoStr;
    }
  }

  function formatBanCategory(cat, st) {
    const kycSuffix = (st && st.kyc && st.kyc.status) ? ` | KYC: ${st.kyc.status}` : '';
    const bootCode = (st && st.bootstrap && st.bootstrap.error_code) ? ` [${st.bootstrap.error_code}]` : '';
    if (!cat) {
      if (st && st.standing === 'good_standing') return `无封禁记录 (正常)${kycSuffix}`;
      return `--${bootCode}${kycSuffix}`;
    }
    const map = {
      other: 'other · 异地风控 / KYC 身份核验失败 / Apple IAP 升级触发异常审查',
      violation_of_terms: 'violation_of_terms · 违反服务条款 (ToS / AUP 策略拦截)',
      underage: 'underage · 疑似未成年 (<18岁) 触发年龄核验锁定',
      automation: 'automation · 自动化脚本 / 高频调用风控拦截',
      billing: 'billing · 支付拒付 / 账单风控拦截'
    };
    const desc = map[cat] || `${cat} · 平台风控策略限制`;
    return `${desc}${bootCode}${kycSuffix}`;
  }

  function formatPlanTier(tier) {
    if (!tier) return '未知 / Free';
    const map = {
      claude_pro: 'Claude Pro ($20)',
      claude_max: 'Claude Max',
      claude_team: 'Claude Team',
      enterprise: 'Enterprise',
      free: 'Claude Free'
    };
    return map[tier] || tier;
  }

  function renderAccountStanding(st) {
    if (!st || typeof st !== 'object' || (!st.standing && !st.bootstrap && !st.appeal && !st.deletion)) {
      if (standingBadge) {
        standingBadge.textContent = '待检测';
        standingBadge.className = 'standing-badge badge-neutral';
      }
      return;
    }

    const standing = st.standing || (st.bootstrap && st.bootstrap.status === 403 ? 'bad_standing' : 'unknown');
    if (standing === 'bad_standing') {
      if (standingBadge) {
        standingBadge.textContent = '🔴 已封禁';
        standingBadge.className = 'standing-badge badge-bad';
      }
      if (stStanding) {
        stStanding.textContent = '🔴 已封禁停权 (bad_standing)';
        stStanding.style.color = '#f87171';
      }
    } else if (standing === 'good_standing') {
      if (standingBadge) {
        standingBadge.textContent = '🟢 正常';
        standingBadge.className = 'standing-badge badge-good';
      }
      if (stStanding) {
        const emailInfo = (st.bootstrap && st.bootstrap.account_email) ? ` · ${st.bootstrap.account_email}` : '';
        stStanding.textContent = `🟢 正常可用 (good_standing)${emailInfo}`;
        stStanding.style.color = '#34d399';
      }
    } else if (standing === 'restricted') {
      if (standingBadge) {
        standingBadge.textContent = '🟠 受限';
        standingBadge.className = 'standing-badge badge-warn';
      }
      if (stStanding) {
        stStanding.textContent = '🟠 组织或权限受限 (restricted)';
        stStanding.style.color = '#fbbf24';
      }
    } else if (standing === 'unauthenticated') {
      if (standingBadge) {
        standingBadge.textContent = '⚪ 未登录';
        standingBadge.className = 'standing-badge badge-neutral';
      }
      if (stStanding) {
        stStanding.textContent = '⚪ 未登录 Claude.ai 或会话已过期 (401)';
        stStanding.style.color = '#94a3b8';
      }
    } else {
      if (standingBadge) {
        standingBadge.textContent = '已捕获';
        standingBadge.className = 'standing-badge badge-neutral';
      }
      if (stStanding) {
        stStanding.textContent = String(standing);
        stStanding.style.color = '#cbd5e1';
      }
    }

    // 封禁原因
    if (stBanReason) {
      stBanReason.textContent = formatBanCategory(st.ban_category, st);
      stBanReason.style.color = st.ban_category ? '#fca5a5' : '#cbd5e1';
    }

    // 封禁时间与原套餐
    if (stBannedAtTier) {
      const timeStr = formatLocalTime(st.banned_at);
      const tierStr = st.prev_plan_tier ? `原套餐: ${formatPlanTier(st.prev_plan_tier)}` : '';
      if (timeStr && tierStr) {
        stBannedAtTier.textContent = `${timeStr} · ${tierStr}`;
      } else if (timeStr) {
        stBannedAtTier.textContent = timeStr;
      } else if (tierStr) {
        stBannedAtTier.textContent = tierStr;
      } else {
        stBannedAtTier.textContent = standing === 'good_standing' ? '无封禁记录' : '--';
      }
    }

    // 受影响组织
    if (stBannedOrgs) {
      if (Array.isArray(st.banned_orgs) && st.banned_orgs.length > 0) {
        stBannedOrgs.textContent = st.banned_orgs
          .map(o => `[${o.org_type || 'org'}] ${o.name || (o.uuid ? o.uuid.slice(0, 8) : '未知')}`)
          .join(' ； ');
        stBannedOrgs.style.color = '#fcd34d';
      } else {
        stBannedOrgs.textContent = standing === 'bad_standing' ? '全账号级封禁' : '无受限组织';
        stBannedOrgs.style.color = '#cbd5e1';
      }
    }

    // 申诉进度
    if (stAppealStatus) {
      const ap = st.appeal;
      if (!ap || ap.status === null) {
        stAppealStatus.textContent = standing === 'bad_standing'
          ? '⚪ 未提交申诉 (可前往 /restricted/submit 提交)'
          : '无需申诉';
        stAppealStatus.style.color = '#94a3b8';
      } else if (ap.status === 'open') {
        const subTime = formatLocalTime(ap.created_at) || '近期';
        const eta = st.review_eta_days || 10;
        stAppealStatus.textContent = `🟡 审核中 (open) · 提交于 ${subTime} · 预计 ${eta} 天回复`;
        stAppealStatus.style.color = '#fbbf24';
      } else if (ap.status === 'approved') {
        stAppealStatus.textContent = '🟢 申诉通过 · 账号已恢复 (approved)';
        stAppealStatus.style.color = '#34d399';
      } else if (ap.status === 'rejected') {
        stAppealStatus.textContent = '🔴 永久封禁驳回 · 最终裁决不可恢复 (rejected)';
        stAppealStatus.style.color = '#f87171';
      } else {
        stAppealStatus.textContent = `状态: ${ap.status}`;
      }
    }

    // 数据导出与账单状态
    if (stExportBilling) {
      const parts = [];
      if (st.export_policy) {
        const expLabel = st.export_policy === 'allow'
          ? '允许全量导出 (allow)'
          : (st.export_policy === 'profile_only' ? '仅资料导出 (profile_only)' : st.export_policy);
        parts.push(`导出: ${expLabel}`);
      }
      if (st.deletion && typeof st.deletion === 'object') {
        if (st.deletion.deletable) {
          parts.push('注销: 允许删除');
        } else {
          const reasons = Array.isArray(st.deletion.reasons) && st.deletion.reasons.length
            ? st.deletion.reasons.join(',')
            : '锁定';
          const billHint = reasons.includes('active_billing') ? ' (活跃订阅锁定)' : '';
          parts.push(`注销: 禁止 [${reasons}${billHint}]`);
        }
      }
      stExportBilling.textContent = parts.length > 0 ? parts.join(' | ') : '--';
    }
  }

  // 直接从扩展上下文请求 Claude 账号状态接口 (当没有打开的标签页或标签页未刷新时兜底)
  async function directPopupStandingProbe() {
    const probed = {
      source: 'popup_direct_probe',
      updatedAt: Date.now()
    };
    const opts = {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json' },
      cache: 'no-store'
    };
    const [stRes, apRes, delRes] = await Promise.allSettled([
      fetch('https://claude.ai/api/account/standing', opts),
      fetch('https://claude.ai/api/account/current_appeal', opts),
      fetch('https://claude.ai/api/account/deletion-allowed', opts)
    ]);

    if (stRes.status === 'fulfilled' && stRes.value) {
      probed.standingHttpStatus = stRes.value.status;
      if (stRes.value.ok) {
        const d = await stRes.value.json();
        if (d && typeof d === 'object') {
          Object.assign(probed, {
            standing: d.standing || 'unknown',
            ban_category: d.ban_category ?? null,
            banned_at: d.banned_at ?? null,
            org_type: d.org_type ?? 'consumer',
            prev_plan_tier: d.prev_plan_tier ?? null,
            export_policy: d.export_policy ?? null,
            banned_orgs: Array.isArray(d.banned_orgs) ? d.banned_orgs : [],
            review_eta_days: d.review_eta_days ?? 10,
            age_verification_url: d.age_verification_url ?? null,
            has_active_org: d.has_active_org ?? null,
            restricted_hcaptcha_mode: d.restricted_hcaptcha_mode ?? null,
            reinstatement_credit_cents: d.reinstatement_credit_cents ?? null
          });
        }
      } else if (stRes.value.status === 401 || stRes.value.status === 403) {
        probed.standing = stRes.value.status === 401 ? 'unauthenticated' : 'restricted';
      }
    }

    if (apRes.status === 'fulfilled' && apRes.value && apRes.value.ok) {
      const d = await apRes.value.json();
      if (d === null) {
        probed.appeal = { status: null, created_at: null, questionnaire: null };
      } else if (d && typeof d === 'object') {
        probed.appeal = {
          status: d.status || 'open',
          created_at: d.created_at || null,
          questionnaire: d.questionnaire || null
        };
      }
    }

    if (delRes.status === 'fulfilled' && delRes.value && delRes.value.ok) {
      const d = await delRes.value.json();
      if (d && typeof d === 'object') {
        probed.deletion = {
          deletable: Boolean(d.deletable),
          reasons: Array.isArray(d.reasons) ? d.reasons : [],
          display_message: d.display_message || null
        };
      }
    }

    return probed;
  }

  function triggerAccountStandingCheck() {
    if (btnCheckStanding) {
      btnCheckStanding.classList.add('loading');
      btnCheckStanding.textContent = '⏳ 正在实时检测账号状态与封禁原因...';
    }

    chrome.tabs.query({ url: ['https://claude.ai/*'] }, (tabs) => {
      const targetTab = (tabs && tabs.length > 0) ? (tabs.find(t => t.active) || tabs[0]) : null;

      const finishWithReport = (newReport) => {
        chrome.storage.local.get(['accountStanding'], (data) => {
          const prev = (data && data.accountStanding && typeof data.accountStanding === 'object')
            ? data.accountStanding
            : {};
          const merged = Object.assign({}, prev, newReport || {}, { updatedAt: Date.now() });
          chrome.storage.local.set({ accountStanding: merged }, () => {
            renderAccountStanding(merged);
            if (btnCheckStanding) {
              btnCheckStanding.classList.remove('loading');
              btnCheckStanding.textContent = '🔍 立即检测账号状态与封禁原因';
            }
          });
        });
      };

      if (targetTab && targetTab.id) {
        chrome.tabs.sendMessage(targetTab.id, { action: 'probeAccountStanding' }, (res) => {
          if (!chrome.runtime.lastError && res && res.accountStanding) {
            finishWithReport(res.accountStanding);
          } else {
            directPopupStandingProbe().then(finishWithReport).catch(() => finishWithReport({}));
          }
        });
      } else {
        directPopupStandingProbe().then(finishWithReport).catch(() => finishWithReport({}));
      }
    });
  }

  // 国旗 Emoji 映射
  function getFlagEmoji(countryCode) {
    if (!countryCode) return '🌐';
    const code = countryCode.toUpperCase();
    if (code === 'TW') return '🇹🇼';
    if (code === 'US') return '🇺🇸';
    if (code === 'JP') return '🇯🇵';
    if (code === 'SG') return '🇸🇬';
    if (code === 'GB' || code === 'UK') return '🇬🇧';
    if (code === 'HK') return '🇭🇰';
    if (code === 'DE') return '🇩🇪';
    if (code === 'CA') return '🇨🇦';
    if (code === 'AU') return '🇦🇺';
    if (code === 'FR') return '🇫🇷';
    if (code === 'KR') return '🇰🇷';
    return '🌐';
  }

  // 渲染节点与状态信息
  function renderNodeInfo(node, mode, activeProfile) {
    const prof = activeProfile || (node ? node : null);
    if (node && node.ip) {
      nodeFlag.textContent = getFlagEmoji(node.countryCode);
      const locText = [node.country, node.city || node.region].filter(Boolean).join(' · ');
      nodeLocation.textContent = locText || '已探测到节点';
      nodeIp.textContent = node.ip || '--';
      nodeTimezone.textContent = `${node.timeZone} (${node.tzName || 'UTC'})`;
      nodeLang.textContent = (node.languages && node.languages.length) ? node.languages.slice(0, 2).join(', ') : (node.language || '--');
      nodeIsp.textContent = [node.isp, node.asn].filter(Boolean).join(' · ') || '网络正常';
    } else if (prof) {
      nodeFlag.textContent = getFlagEmoji(prof.countryCode);
      nodeLocation.textContent = prof.name || '默认配置';
      nodeIp.textContent = prof.ip || '探测中 / 本地保底';
      nodeTimezone.textContent = `${prof.timeZone} (${prof.tzName || 'UTC'})`;
      nodeLang.textContent = (prof.languages && prof.languages.length) ? prof.languages.slice(0, 2).join(', ') : (prof.language || '--');
      nodeIsp.textContent = prof.isp || '本地隐私防护已激活';
    } else {
      nodeFlag.textContent = '🌐';
      nodeLocation.textContent = '检测网络中...';
      nodeIp.textContent = '--';
      nodeTimezone.textContent = '--';
      nodeLang.textContent = '--';
      nodeIsp.textContent = '--';
    }

    if (mode === 'auto') {
      if (node && node.ip) {
        syncStatus.textContent = '已自动识别当前 VPN 节点，时区零偏差';
        syncStatus.style.color = '#38bdf8';
      } else {
        syncStatus.textContent = '正在探测当前节点，已采用安全时区保底';
        syncStatus.style.color = '#f59e0b';
      }
    } else if (mode === 'taiwan') {
      syncStatus.textContent = '已锁定台湾专线画像 (HiNet AS3462)';
      syncStatus.style.color = '#34d399';
    } else if (mode === 'us') {
      syncStatus.textContent = '已锁定美国原生画像 (美西 Pacific)';
      syncStatus.style.color = '#a78bfa';
    }
  }

  // 更新卡片激活样式
  function updateCardStyles(selectedMode) {
    const cardMap = {
      auto: cardAuto,
      taiwan: cardTaiwan,
      us: cardUS
    };

    Object.keys(cardMap).forEach(key => {
      if (cardMap[key]) {
        if (key === selectedMode) {
          cardMap[key].classList.add('active');
        } else {
          cardMap[key].classList.remove('active');
        }
      }
    });
  }

  // 加载当前配置
  function loadConfig() {
    chrome.runtime.sendMessage({ action: 'getConfig' }, (response) => {
      if (response && response.config) {
        const conf = response.config;
        const currentMode = conf.mode || 'auto';
        
        const radio = document.querySelector(`input[name="mode"][value="${currentMode}"]`);
        if (radio) radio.checked = true;

        updateCardStyles(currentMode);
        renderNodeInfo(conf.detectedNode, currentMode, conf.activeProfile);
        if (conf.accountStanding) {
          renderAccountStanding(conf.accountStanding);
        }

        // 如果尚未获取到节点信息，自动触发一次检测
        if (!conf.detectedNode) {
          refreshEgress(false);
        }
      }
    });
  }

  // 监听 storage 变化实时刷新账号封禁诊断台
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes.accountStanding && changes.accountStanding.newValue) {
        renderAccountStanding(changes.accountStanding.newValue);
      }
    });
  } catch (e) {}

  // 触发刷新节点
  function refreshEgress(force = true) {
    if (btnRefreshNode) {
      btnRefreshNode.classList.add('loading');
      btnRefreshNode.textContent = '⏳ 探测中...';
    }

    chrome.runtime.sendMessage({ action: 'refreshNode', force }, (res) => {
      if (btnRefreshNode) {
        btnRefreshNode.classList.remove('loading');
        btnRefreshNode.textContent = '🔄 重新识别';
      }
      if (res && res.config) {
        const conf = res.config;
        const currentMode = conf.mode || 'auto';
        updateCardStyles(currentMode);
        renderNodeInfo(conf.detectedNode, currentMode, conf.activeProfile);
      }
    });
  }

  // 模式单选切换监听
  radios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      const newMode = e.target.value;
      updateCardStyles(newMode);
      chrome.runtime.sendMessage({ action: 'setMode', mode: newMode }, (res) => {
        if (res && res.status === 'ok') {
          chrome.storage.local.get(null, (conf) => {
            renderNodeInfo(conf.detectedNode, newMode, res.activeProfile);
          });
        }
      });
    });
  });

  // 刷新按钮
  if (btnRefreshNode) {
    btnRefreshNode.addEventListener('click', () => {
      refreshEgress(true);
    });
  }

  // 立即检测账号状态与封禁原因按钮
  if (btnCheckStanding) {
    btnCheckStanding.addEventListener('click', () => {
      triggerAccountStandingCheck();
    });
  }

  // 底部快捷操作
  if (btnOpenClaude) {
    btnOpenClaude.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://claude.ai/' });
    });
  }

  if (btnTestYouClaude) {
    btnTestYouClaude.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://youclaude.com/' });
    });
  }

  if (btnTestBewild) {
    btnTestBewild.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://bewild.ai/network-detection?source=claude-subscribe' });
    });
  }

  if (btnTestLeak) {
    btnTestLeak.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://browserleaks.com/webrtc' });
    });
  }

  if (btnTestIp) {
    btnTestIp.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://iphey.com/' });
    });
  }

  // 初始化
  loadConfig();
});
