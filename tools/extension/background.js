/**
 * Claude Shield & Anti-Fingerprint Cloak - Background Service Worker v1.2.1
 * 支持当前 VPN 出口 IP / 时区 / 语言全自动实时对齐与 WebRTC 防泄漏
 */

const PRESETS = {
  taiwan: {
    mode: 'taiwan',
    name: '台湾住宅专线 (HiNet AS3462)',
    timeZone: 'Asia/Taipei',
    tzName: 'Taipei Standard Time',
    language: 'zh-TW',
    languages: ['zh-TW', 'zh', 'en-US', 'en'],
    locale: 'zh-TW',
    countryCode: 'TW',
    country: 'Taiwan'
  },
  us: {
    mode: 'us',
    name: '美国原生西海岸 (美西 Pacific)',
    timeZone: 'America/Los_Angeles',
    tzName: 'Pacific Time',
    language: 'en-US',
    languages: ['en-US', 'en'],
    locale: 'en-US',
    countryCode: 'US',
    country: 'United States'
  }
};

const DEFAULT_CONFIG = {
  mode: 'auto',
  profile: 'auto',
  webrtcShieldEnabled: true,
  canvasNoiseEnabled: true,
  audioNoiseEnabled: true,
  stripTrackersEnabled: true,
  detectedNode: null,
  activeProfile: PRESETS.us,
  lastChecked: 0
};

// 语言与时区智能映射规则
function getLanguagesForCountry(countryCode) {
  const code = (countryCode || '').toUpperCase();
  switch (code) {
    case 'TW':
      return ['zh-TW', 'zh', 'en-US', 'en'];
    case 'HK':
      return ['zh-HK', 'zh', 'en-US', 'en'];
    case 'JP':
      return ['ja', 'en-US', 'en'];
    case 'SG':
      return ['en-SG', 'en-US', 'zh-SG', 'en'];
    case 'GB':
    case 'UK':
      return ['en-GB', 'en-US', 'en'];
    case 'CA':
      return ['en-CA', 'en-US', 'fr-CA', 'en'];
    case 'AU':
      return ['en-AU', 'en-US', 'en'];
    case 'DE':
      return ['de-DE', 'de', 'en-US', 'en'];
    case 'FR':
      return ['fr-FR', 'fr', 'en-US', 'en'];
    case 'KR':
      return ['ko-KR', 'ko', 'en-US', 'en'];
    case 'US':
    default:
      return ['en-US', 'en'];
  }
}

function getPrimaryLanguageForCountry(countryCode) {
  return getLanguagesForCountry(countryCode)[0];
}

function getLocaleForCountry(countryCode) {
  const code = (countryCode || '').toUpperCase();
  if (code === 'TW') return 'zh-TW';
  if (code === 'HK') return 'zh-HK';
  if (code === 'JP') return 'ja-JP';
  if (code === 'SG') return 'en-SG';
  if (code === 'GB') return 'en-GB';
  if (code === 'DE') return 'de-DE';
  return 'en-US';
}

function getFallbackTimezoneForCountry(countryCode) {
  const code = (countryCode || '').toUpperCase();
  switch (code) {
    case 'TW': return 'Asia/Taipei';
    case 'HK': return 'Asia/Hong_Kong';
    case 'JP': return 'Asia/Tokyo';
    case 'SG': return 'Asia/Singapore';
    case 'GB': return 'Europe/London';
    case 'DE': return 'Europe/Berlin';
    case 'FR': return 'Europe/Paris';
    case 'AU': return 'Australia/Sydney';
    case 'CA': return 'America/Toronto';
    case 'US': default: return 'America/Los_Angeles';
  }
}

// 针对 Cloudflare 边缘节点（三字代码）进行精准时区解析
function getTimezoneForColo(colo, countryCode) {
  const c = (colo || '').toUpperCase();
  // 美西 / Pacific
  if (['SJC', 'LAX', 'SFO', 'SEA', 'PDX', 'SAN', 'PHX', 'LAS', 'SLC'].includes(c)) return 'America/Los_Angeles';
  // 美中 / Central
  if (['ORD', 'DFW', 'IAH', 'MSP', 'STL', 'MCI'].includes(c)) return 'America/Chicago';
  // 美山地 / Mountain
  if (['DEN'].includes(c)) return 'America/Denver';
  // 美东 / Eastern
  if (['IAD', 'EWR', 'JFK', 'BOS', 'ATL', 'MIA', 'CLT'].includes(c)) return 'America/New_York';
  // 台湾
  if (['TPE', 'KHH'].includes(c)) return 'Asia/Taipei';
  // 香港
  if (['HKG'].includes(c)) return 'Asia/Hong_Kong';
  // 日本
  if (['NRT', 'HND', 'KIX'].includes(c)) return 'Asia/Tokyo';
  // 新加坡
  if (['SIN'].includes(c)) return 'Asia/Singapore';
  // 英国
  if (['LHR', 'MAN', 'EDI'].includes(c)) return 'Europe/London';
  // 德国
  if (['FRA', 'BER', 'MUC'].includes(c)) return 'Europe/Berlin';

  return getFallbackTimezoneForCountry(countryCode);
}

// 自动探测当前 VPN / 代理出口网络环境
async function detectEgressNetwork() {
  // 1. 首选方案: ipwho.is (信息最全, 无密钥, 支持精准时区与 ASN)
  let timeoutId;
  try {
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), 3500);
    const res = await fetch('https://ipwho.is/', {
      cache: 'no-store',
      signal: controller.signal
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.success && data.timezone) {
        return {
          ip: data.ip,
          country: data.country,
          countryCode: data.country_code,
          city: data.city || '',
          region: data.region || '',
          isp: data.connection ? (data.connection.isp || data.connection.org || '') : '',
          org: data.connection ? data.connection.org : '',
          asn: data.connection && data.connection.asn ? `AS${data.connection.asn}` : '',
          timeZone: data.timezone.id,
          tzName: data.timezone.abbr || data.timezone.id,
          offsetSeconds: data.timezone.offset,
          languages: getLanguagesForCountry(data.country_code),
          language: getPrimaryLanguageForCountry(data.country_code),
          locale: getLocaleForCountry(data.country_code),
          mode: 'auto',
          name: `自动检测 (${data.country} · ${data.city || data.region || '节点'})`,
          detectedAt: Date.now()
        };
      }
    }
  } catch (e) {
    console.debug('[ClaudeShield] ipwho.is detection error, trying fallback:', e);
  } finally {
    clearTimeout(timeoutId);
  }

  // 2. 备用方案 1: freeipapi.com
  try {
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), 3500);
    const res = await fetch('https://freeipapi.com/api/json', {
      cache: 'no-store',
      signal: controller.signal
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.ipAddress) {
        const tz = (Array.isArray(data.timeZones) && data.timeZones.length > 0)
          ? data.timeZones[0]
          : (data.timeZone || getFallbackTimezoneForCountry(data.countryCode));
        return {
          ip: data.ipAddress,
          country: data.countryName,
          countryCode: data.countryCode,
          city: data.cityName || '',
          region: data.regionName || '',
          isp: data.asnOrganization || '',
          org: data.asnOrganization || '',
          asn: data.asn ? `AS${data.asn}` : '',
          timeZone: tz,
          tzName: tz.split('/').pop().replace(/_/g, ' '),
          languages: getLanguagesForCountry(data.countryCode),
          language: getPrimaryLanguageForCountry(data.countryCode),
          locale: getLocaleForCountry(data.countryCode),
          mode: 'auto',
          name: `自动检测 (${data.countryName} · ${data.cityName || '节点'})`,
          detectedAt: Date.now()
        };
      }
    }
  } catch (e) {
    console.debug('[ClaudeShield] freeipapi.com error, trying cloudflare trace:', e);
  } finally {
    clearTimeout(timeoutId);
  }

  // 3. 备用方案 2: Cloudflare Trace (优先 1.1.1.1, 次选 cloudflare.com)
  const cfEndpoints = ['https://1.1.1.1/cdn-cgi/trace', 'https://cloudflare.com/cdn-cgi/trace'];
  for (const endpoint of cfEndpoints) {
    try {
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(endpoint, {
        cache: 'no-store',
        signal: controller.signal
      });
      if (res.ok) {
        const text = await res.text();
        const lines = text.split('\n');
        const trace = {};
        lines.forEach(l => {
          const parts = l.split('=');
          if (parts[0] && parts[1]) trace[parts[0].trim()] = parts[1].trim();
        });
        if (trace.ip) {
          const cCode = trace.loc || 'US';
          const tz = getTimezoneForColo(trace.colo, cCode);
          return {
            ip: trace.ip,
            country: cCode,
            countryCode: cCode,
            city: trace.colo || '',
            region: '',
            isp: 'Cloudflare Edge',
            org: '',
            asn: '',
            timeZone: tz,
            tzName: tz.split('/').pop().replace(/_/g, ' '),
            languages: getLanguagesForCountry(cCode),
            language: getPrimaryLanguageForCountry(cCode),
            locale: getLocaleForCountry(cCode),
            mode: 'auto',
            name: `自动检测 (${cCode} · Colo ${trace.colo || ''})`,
            detectedAt: Date.now()
          };
        }
      }
    } catch (e) {
      console.debug(`[ClaudeShield] ${endpoint} trace error:`, e);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  return null;
}

// 刷新并对齐当前配置
async function refreshNetworkProfile(force = false) {
  const current = await chrome.storage.local.get(null);
  const now = Date.now();

  // 若非强制刷新且在 30 秒内已检测过，则跳过
  if (!force && current.lastChecked && (now - current.lastChecked < 30000) && current.detectedNode) {
    return current;
  }

  const detected = await detectEgressNetwork();
  const mode = current.mode || 'auto';

  let activeProfile;
  if (mode === 'auto') {
    activeProfile = detected || current.detectedNode || PRESETS.us;
  } else if (PRESETS[mode]) {
    activeProfile = PRESETS[mode];
  } else {
    activeProfile = PRESETS.taiwan;
  }

  const newConfig = {
    ...DEFAULT_CONFIG,
    ...current,
    mode,
    detectedNode: detected || current.detectedNode,
    activeProfile,
    lastChecked: now
  };

  await chrome.storage.local.set(newConfig);
  broadcastProfileChange(activeProfile);
  console.log(`[ClaudeShield] 网络对齐完成. 模式: ${mode}, 出口: ${activeProfile.ip || 'Preset'}, 时区: ${activeProfile.timeZone}`);
  return newConfig;
}

// 强制设置 WebRTC 隐私策略 (禁用非代理 UDP，杜绝 IPv6 / 内网泄漏)
function enforceWebRTCPrivacy() {
  if (chrome.privacy && chrome.privacy.network && chrome.privacy.network.webRTCIPHandlingPolicy) {
    chrome.privacy.network.webRTCIPHandlingPolicy.set({
      value: 'disable_non_proxied_udp'
    }, () => {
      if (chrome.runtime.lastError) {
        console.warn('[ClaudeShield] 设置 WebRTC 策略异常:', chrome.runtime.lastError);
      } else {
        console.log('[ClaudeShield] WebRTC 防泄漏策略生效: disable_non_proxied_udp');
      }
    });
  }
}

// 同步动态 Accept-Language 请求头规则并与所有活跃标签页广播配置更新
function broadcastProfileChange(newProfile) {
  if (chrome.declarativeNetRequest && chrome.declarativeNetRequest.updateDynamicRules && newProfile) {
    const isEn = newProfile.language && newProfile.language.toLowerCase().startsWith('en');
    const acceptLangVal = isEn
      ? 'en-US,en;q=0.9'
      : 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7';
    chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: [1003],
      addRules: [
        {
          id: 1003,
          priority: 2,
          action: {
            type: 'modifyHeaders',
            requestHeaders: [
              {
                header: 'Accept-Language',
                operation: 'set',
                value: acceptLangVal
              }
            ]
          },
          condition: {
            requestDomains: [
              'claude.ai',
              'anthropic.com',
              'hcaptcha.com',
              'datadoghq.com',
              'withpersona.com',
              'persona.com'
            ],
            resourceTypes: [
              'main_frame',
              'sub_frame',
              'stylesheet',
              'script',
              'image',
              'font',
              'object',
              'xmlhttprequest',
              'ping',
              'csp_report',
              'media',
              'websocket',
              'other'
            ]
          }
        }
      ]
    }).catch(() => {});
  }

  if (!chrome.tabs) return;
  chrome.tabs.query({
    url: [
      'https://claude.ai/*',
      'https://*.anthropic.com/*',
      'https://*.withpersona.com/*',
      'https://*.persona.com/*',
      'https://*.hcaptcha.com/*',
      'https://bewild.ai/*',
      'https://*.bewild.ai/*',
      'https://browserleaks.com/*',
      'https://*.browserleaks.com/*',
      'https://iphey.com/*',
      'https://*.iphey.com/*',
      'https://whoer.net/*',
      'https://*.whoer.net/*'
    ]
  }, (tabs) => {
    if (tabs && tabs.length > 0) {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'applyProfile',
          profile: newProfile
        }).catch(() => {});
      });
    }
  });
}

// 扩展生命周期事件
chrome.runtime.onInstalled.addListener(() => {
  enforceWebRTCPrivacy();
  chrome.storage.local.get(null, (existing) => {
    if (!existing || !existing.mode) {
      chrome.storage.local.set(DEFAULT_CONFIG, () => {
        refreshNetworkProfile(true);
      });
    } else {
      refreshNetworkProfile(true);
    }
  });
});

chrome.runtime.onStartup.addListener(() => {
  enforceWebRTCPrivacy();
  refreshNetworkProfile(false);
});

// 监听标签页打开/刷新 Claude 或检测站点，智能触发探测
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading' && tab.url) {
    const isTarget = ['claude.ai', 'anthropic.com', 'bewild.ai', 'browserleaks.com', 'iphey.com', 'whoer.net']
      .some(domain => tab.url.includes(domain));
    if (isTarget) {
      chrome.storage.local.get(['lastChecked'], (data) => {
        // 距离上次检测超过 3 分钟，静默在后台更新一次，确保节点变更及时同步
        if (!data.lastChecked || (Date.now() - data.lastChecked > 180000)) {
          refreshNetworkProfile(false);
        }
      });
    }
  }
});

// 消息路由监听器
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getConfig') {
    chrome.storage.local.get(null, (config) => {
      const result = Object.keys(config).length ? config : DEFAULT_CONFIG;
      sendResponse({ status: 'ok', config: result });
    });
    return true;
  }

  if (request.action === 'refreshNode') {
    refreshNetworkProfile(true).then((updated) => {
      sendResponse({ status: 'ok', config: updated });
    }).catch(err => {
      sendResponse({ status: 'error', error: err.message });
    });
    return true;
  }

  if (request.action === 'setMode') {
    const newMode = request.mode;
    chrome.storage.local.get(null, (current) => {
      let activeProfile;
      if (newMode === 'auto') {
        activeProfile = current.detectedNode || PRESETS.us;
      } else if (PRESETS[newMode]) {
        activeProfile = PRESETS[newMode];
      } else {
        activeProfile = PRESETS.taiwan;
      }

      chrome.storage.local.set({
        mode: newMode,
        profile: newMode,
        activeProfile
      }, () => {
        broadcastProfileChange(activeProfile);
        sendResponse({ status: 'ok', activeProfile, mode: newMode });
      });
    });
    return true;
  }

  if (request.action === 'updateProfile') {
    // 兼容旧接口
    const profileKey = request.profile;
    const mode = (profileKey === 'taiwan' || profileKey === 'us') ? profileKey : 'auto';
    chrome.storage.local.set({ mode, profile: mode }, () => {
      refreshNetworkProfile(false).then(() => {
        sendResponse({ status: 'ok' });
      });
    });
    return true;
  }
});
