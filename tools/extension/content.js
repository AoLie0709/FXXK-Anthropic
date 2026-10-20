/**
 * Claude Shield & Anti-Fingerprint Cloak - Content Script (ISOLATED World) v1.5.0
 * 同步扩展最新环境配置到网页运行时，并被动/主动采集 Claude 账号封禁状态、原因、申诉进度与 KYC 诊断信息
 */

(function() {
  'use strict';

  const SYNC_EVENT_NAME = '__cs_dispatch_sync_v2__';
  const STANDING_EVENT_NAME = '__CLAUDE_SHIELD_ACCOUNT_STANDING__';
  const PROBE_TRIGGER_EVENT = '__CLAUDE_SHIELD_PROBE_STANDING__';

  function syncProfile(profileObj) {
    if (!profileObj || typeof profileObj !== 'object') return;

    // 清理历史版本残留的本地存储特征字段与字典追踪缓存，确保目标源 localStorage 纯净
    try {
      localStorage.removeItem('__claude_shield_profile_data__');
      localStorage.removeItem('__claude_shield_profile__');
      localStorage.removeItem('__c_shld_s__');
      if (/claude\.ai|anthropic\.com/i.test(window.location.hostname)) {
        localStorage.removeItem('persisted.dcz_keep');
        localStorage.removeItem('persisted.atm_event_hold_held');
      }
    } catch (e) {}

    // 通过专属私有 DOM CustomEvent 瞬间热同步到 MAIN 运行时
    try {
      document.dispatchEvent(new CustomEvent(SYNC_EVENT_NAME, { detail: profileObj }));
    } catch (e) {}
  }

  // 保存账号状态报告到 chrome.storage.local (accountStanding)
  function persistAccountStanding(incoming) {
    if (!incoming || typeof incoming !== 'object') return;
    try {
      chrome.storage.local.get(['accountStanding'], (data) => {
        const prev = (data && data.accountStanding && typeof data.accountStanding === 'object')
          ? data.accountStanding
          : {};
        const merged = Object.assign({}, prev, incoming, {
          updatedAt: Date.now()
        });
        chrome.storage.local.set({ accountStanding: merged });
      });
    } catch (e) {}
  }

  // 监听来自 inject.js 的被动/主动账号状态报告 (CustomEvent + postMessage 双兼容)
  try {
    document.addEventListener(STANDING_EVENT_NAME, (event) => {
      if (event && event.detail && typeof event.detail === 'object') {
        persistAccountStanding(event.detail);
      }
    });

    window.addEventListener('message', (event) => {
      if (event && event.source === window && event.data && event.data.type === STANDING_EVENT_NAME && event.data.payload) {
        persistAccountStanding(event.data.payload);
      }
    });
  } catch (e) {}

  // 主动探测当前页面下的 Claude 账号状态、申诉进度与删除/账单锁
  async function runDirectStandingProbe() {
    const result = {
      source: 'active_probe',
      probedUrl: window.location.href,
      updatedAt: Date.now()
    };

    try {
      const [stRes, apRes, delRes] = await Promise.allSettled([
        fetch('https://claude.ai/api/account/standing', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' },
          cache: 'no-store'
        }),
        fetch('https://claude.ai/api/account/current_appeal', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' },
          cache: 'no-store'
        }),
        fetch('https://claude.ai/api/account/deletion-allowed', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' },
          cache: 'no-store'
        })
      ]);

      if (stRes.status === 'fulfilled' && stRes.value) {
        result.standingHttpStatus = stRes.value.status;
        if (stRes.value.ok) {
          const stData = await stRes.value.json();
          if (stData && typeof stData === 'object') {
            Object.assign(result, {
              standing: stData.standing || 'unknown',
              ban_category: stData.ban_category ?? null,
              banned_at: stData.banned_at ?? null,
              org_type: stData.org_type ?? 'consumer',
              prev_plan_tier: stData.prev_plan_tier ?? null,
              export_policy: stData.export_policy ?? null,
              banned_orgs: Array.isArray(stData.banned_orgs) ? stData.banned_orgs : [],
              review_eta_days: stData.review_eta_days ?? 10,
              age_verification_url: stData.age_verification_url ?? null,
              has_active_org: stData.has_active_org ?? null,
              restricted_hcaptcha_mode: stData.restricted_hcaptcha_mode ?? null,
              reinstatement_credit_cents: stData.reinstatement_credit_cents ?? null
            });
          }
        } else if (stRes.value.status === 401 || stRes.value.status === 403) {
          result.standing = result.standing || (stRes.value.status === 401 ? 'unauthenticated' : 'restricted');
        }
      }

      if (apRes.status === 'fulfilled' && apRes.value && apRes.value.ok) {
        const apData = await apRes.value.json();
        if (apData === null) {
          result.appeal = { status: null, created_at: null, questionnaire: null };
        } else if (apData && typeof apData === 'object') {
          result.appeal = {
            status: apData.status || 'open',
            created_at: apData.created_at || null,
            questionnaire: apData.questionnaire || null
          };
        }
      }

      if (delRes.status === 'fulfilled' && delRes.value && delRes.value.ok) {
        const delData = await delRes.value.json();
        if (delData && typeof delData === 'object') {
          result.deletion = {
            deletable: Boolean(delData.deletable),
            reasons: Array.isArray(delData.reasons) ? delData.reasons : [],
            display_message: delData.display_message || null
          };
        }
      }
    } catch (e) {
      result.probeError = e.message;
    }

    return result;
  }

  // 1. 初始拉取配置并同步
  try {
    chrome.storage.local.get(['activeProfile', 'detectedNode', 'mode'], (data) => {
      if (data && data.activeProfile) {
        syncProfile(data.activeProfile);
      } else if (data && data.detectedNode) {
        syncProfile(data.detectedNode);
      }
    });
  } catch (e) {}

  // 2. 响应配置动态变更
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes.activeProfile && changes.activeProfile.newValue) {
        syncProfile(changes.activeProfile.newValue);
      }
    });
  } catch (e) {}

  // 3. 响应来自 Background / Popup 的实时指令
  try {
    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
      if (msg && msg.action === 'applyProfile' && msg.profile) {
        syncProfile(msg.profile);
        sendResponse({ status: 'ok' });
        return false;
      }

      if (msg && msg.action === 'probeAccountStanding') {
        if (window.top && window !== window.top) return false;
        // 触发 MAIN world 主动探测，同时执行兜底探测确保一定返回最新结果
        try {
          document.dispatchEvent(new CustomEvent(PROBE_TRIGGER_EVENT));
        } catch (e) {}

        runDirectStandingProbe().then((probed) => {
          chrome.storage.local.get(['accountStanding'], (data) => {
            const prev = (data && data.accountStanding && typeof data.accountStanding === 'object')
              ? data.accountStanding
              : {};
            const merged = Object.assign({}, prev, probed, { updatedAt: Date.now() });
            chrome.storage.local.set({ accountStanding: merged }, () => {
              sendResponse({ status: 'ok', accountStanding: merged });
            });
          });
        });
        return true;
      }
    });
  } catch (e) {}
})();
