/**
 * Claude Shield & Anti-Fingerprint Cloak - Injected Script (MAIN World)
 * Executes at document_start in the webpage context prior to Claude/Cloudflare scripts.
 * Stealth edition: Native function signatures preserved, complete Date & Intl engine,
 * prototype-level Navigator cloaking, non-recursive Canvas micro-noise, airtight WebRTC filter.
 */

(function() {
  'use strict';

  // Prevent multiple injections using non-enumerable Symbol lock
  const INJECT_LOCK = Symbol.for('__cs_runtime_active__');
  if (window[INJECT_LOCK]) return;
  try {
    Object.defineProperty(window, INJECT_LOCK, {
      value: true,
      writable: false,
      configurable: false,
      enumerable: false
    });
    delete window.__CLAUDE_SHIELD_INJECTED__;
  } catch (e) {
    window[INJECT_LOCK] = true;
  }

  // --- 1. Stealth Native Function Wrapper ---
  const nativeToString = Function.prototype.toString;
  const customToStrings = new WeakMap();

  function makeNative(fn, origFn, name) {
    const fnName = name || (origFn ? origFn.name : fn.name);
    try {
      Object.defineProperty(fn, 'name', { value: fnName, configurable: true });
      if (origFn && typeof origFn.length === 'number') {
        Object.defineProperty(fn, 'length', { value: origFn.length, configurable: true });
      }
    } catch (e) {}
    const str = `function ${fnName}() { [native code] }`;
    customToStrings.set(fn, str);
    return fn;
  }

  Function.prototype.toString = function() {
    if (new.target) {
      throw new TypeError('Function.prototype.toString is not a constructor');
    }
    if (customToStrings.has(this)) {
      return customToStrings.get(this);
    }
    return nativeToString.call(this);
  };
  makeNative(Function.prototype.toString, nativeToString, 'toString');

  // --- 2. In-Memory Profile Management (Zero LocalStorage Footprint) ---
  const DEFAULT_PROFILE = {
    name: '台湾住宅专线 (Chunghwa HiNet)',
    timeZone: 'Asia/Taipei',
    language: 'zh-TW',
    languages: ['zh-TW', 'zh', 'en-US', 'en'],
    locale: 'zh-TW',
    tzName: 'Taipei Standard Time'
  };

  const PROFILES = {
    taiwan: {
      name: '台湾住宅专线 (Chunghwa HiNet)',
      timeZone: 'Asia/Taipei',
      language: 'zh-TW',
      languages: ['zh-TW', 'zh', 'en-US', 'en'],
      locale: 'zh-TW',
      tzName: 'Taipei Standard Time'
    },
    us: {
      name: '美国原生西海岸 (Pacific)',
      timeZone: 'America/Los_Angeles',
      language: 'en-US',
      languages: ['en-US', 'en'],
      locale: 'en-US',
      tzName: 'Pacific Daylight Time'
    }
  };

  let active = Object.assign({}, DEFAULT_PROFILE);

  function getEffectiveHostname() {
    try {
      if (window.location && window.location.hostname) return window.location.hostname;
    } catch (e) {}
    try {
      if (window.parent && window.parent !== window && window.parent.location && window.parent.location.hostname) {
        return window.parent.location.hostname;
      }
    } catch (e) {}
    try {
      if (window.top && window.top !== window && window.top.location && window.top.location.hostname) {
        return window.top.location.hostname;
      }
    } catch (e) {}
    try {
      if (document.referrer) return new URL(document.referrer).hostname;
    } catch (e) {}
    return '';
  }

  const effectiveHost = getEffectiveHostname();

  function syncClaudeLocalStorage() {
    try {
      localStorage.removeItem('__claude_shield_profile_data__');
      localStorage.removeItem('__claude_shield_profile__');
      localStorage.removeItem('__c_shld_s__');
      if (/claude\.ai|anthropic\.com/i.test(effectiveHost)) {
        localStorage.removeItem('persisted.dcz_keep');
        localStorage.removeItem('persisted.atm_event_hold_held');
        const targetSpaLocale = (active.language && active.language.toLowerCase().startsWith('en'))
          ? 'en-US'
          : 'zh-Hant';
        localStorage.setItem('spa:locale', targetSpaLocale);
      }
    } catch (e) {}
  }

  syncClaudeLocalStorage();

  // Guard Storage.prototype so dcz_keep & atm_event_hold_held cannot persist cross-session tracking
  try {
    if (/claude\.ai|anthropic\.com/i.test(effectiveHost) && window.Storage && window.Storage.prototype) {
      const origGetItem = window.Storage.prototype.getItem;
      const origSetItem = window.Storage.prototype.setItem;
      if (origGetItem) {
        window.Storage.prototype.getItem = makeNative(function(key) {
          if (key === 'persisted.dcz_keep' || key === 'persisted.atm_event_hold_held') {
            return null;
          }
          if (key === 'spa:locale') {
            return (active.language && active.language.toLowerCase().startsWith('en')) ? 'en-US' : 'zh-Hant';
          }
          return origGetItem.call(this, key);
        }, origGetItem, 'getItem');
      }
      if (origSetItem) {
        window.Storage.prototype.setItem = makeNative(function(key, val) {
          if (key === 'persisted.dcz_keep' || key === 'persisted.atm_event_hold_held') {
            return;
          }
          if (key === 'spa:locale') {
            val = (active.language && active.language.toLowerCase().startsWith('en')) ? 'en-US' : 'zh-Hant';
          }
          return origSetItem.call(this, key, val);
        }, origSetItem, 'setItem');
      }
    }
  } catch (e) {}

  function applyProfilePayload(payload) {
    if (typeof payload === 'object' && payload && payload.timeZone) {
      Object.assign(active, payload);
    } else if (typeof payload === 'string' && PROFILES[payload]) {
      Object.assign(active, PROFILES[payload]);
    }
    syncClaudeLocalStorage();
  }

  // Listen for private synchronous DOM CustomEvent dispatched from content script
  document.addEventListener('__cs_dispatch_sync_v2__', (event) => {
    if (event && event.detail) {
      applyProfilePayload(event.detail);
    }
  });

  // --- 3. High-Accuracy ECMAScript-Compliant Date & Intl Engine ---
  const origDTF = Intl.DateTimeFormat;
  const dtfCache = new Map();
  function getCachedDTF(locales, options) {
    const key = JSON.stringify({ locales, options });
    if (!dtfCache.has(key)) {
      dtfCache.set(key, new origDTF(locales, options));
    }
    return dtfCache.get(key);
  }

  function WrappedDateTimeFormat(locales, options) {
    let opts = options ? Object.assign({}, options) : {};
    if (!opts.timeZone) {
      opts.timeZone = active.timeZone;
    }
    if (!locales && active.locale) {
      locales = active.locale;
    }
    return new origDTF(locales, opts);
  }
  WrappedDateTimeFormat.prototype = origDTF.prototype;
  WrappedDateTimeFormat.supportedLocalesOf = origDTF.supportedLocalesOf;
  Intl.DateTimeFormat = makeNative(WrappedDateTimeFormat, origDTF, 'DateTimeFormat');

  const dayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

  function getDateParts(d, tz) {
    if (Number.isNaN(d.getTime())) return null;
    try {
      const parts = getCachedDTF('en-US', {
        timeZone: tz,
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23',
        timeZoneName: 'long'
      }).formatToParts(d);
      const m = {};
      for (let i = 0; i < parts.length; i++) m[parts[i].type] = parts[i].value;

      const partsNum = getCachedDTF('en-US', {
        timeZone: tz,
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23'
      }).formatToParts(d);
      const mn = {};
      for (let i = 0; i < partsNum.length; i++) mn[partsNum[i].type] = partsNum[i].value;

      const hNum = parseInt(mn.hour, 10);
      const monthIndex = parseInt(mn.month, 10) - 1;
      const dayNum = parseInt(mn.day, 10);
      const yearNum = parseInt(mn.year, 10);
      const minNum = parseInt(mn.minute, 10);
      const secNum = parseInt(mn.second, 10);

      const targetUtcMs = Date.UTC(yearNum, monthIndex, dayNum, hNum, minNum, secNum);
      const actualUtcMs = Date.UTC(
        d.getUTCFullYear(),
        d.getUTCMonth(),
        d.getUTCDate(),
        d.getUTCHours(),
        d.getUTCMinutes(),
        d.getUTCSeconds()
      );
      const offsetMinutes = Math.round((actualUtcMs - targetUtcMs) / 60000);
      const sign = offsetMinutes <= 0 ? '+' : '-';
      const absOffset = Math.abs(offsetMinutes);
      const offH = String(Math.floor(absOffset / 60)).padStart(2, '0');
      const offM = String(absOffset % 60).padStart(2, '0');
      const gmtString = `GMT${sign}${offH}${offM}`;

      return {
        weekday: m.weekday,
        monthName: m.month,
        day: mn.day,
        year: mn.year,
        hour: mn.hour,
        minute: mn.minute,
        second: mn.second,
        tzName: m.timeZoneName || active.tzName || tz,
        gmtString,
        offsetMinutes,
        hNum,
        monthIndex,
        dayNum,
        yearNum,
        minNum,
        secNum,
        dayOfWeek: dayMap[m.weekday] ?? 0
      };
    } catch (e) {
      return null;
    }
  }

  const origToString = Date.prototype.toString;
  const origToDateString = Date.prototype.toDateString;
  const origToTimeString = Date.prototype.toTimeString;
  const origGetTimezoneOffset = Date.prototype.getTimezoneOffset;
  const origGetHours = Date.prototype.getHours;
  const origGetDate = Date.prototype.getDate;
  const origGetDay = Date.prototype.getDay;
  const origGetMonth = Date.prototype.getMonth;
  const origGetFullYear = Date.prototype.getFullYear;
  const origGetMinutes = Date.prototype.getMinutes;
  const origGetSeconds = Date.prototype.getSeconds;
  const origToLocaleString = Date.prototype.toLocaleString;
  const origToLocaleDateString = Date.prototype.toLocaleDateString;
  const origToLocaleTimeString = Date.prototype.toLocaleTimeString;

  Date.prototype.getTimezoneOffset = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.offsetMinutes : origGetTimezoneOffset.call(this);
  }, origGetTimezoneOffset);

  Date.prototype.getHours = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.hNum : origGetHours.call(this);
  }, origGetHours);

  Date.prototype.getDate = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.dayNum : origGetDate.call(this);
  }, origGetDate);

  Date.prototype.getDay = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.dayOfWeek : origGetDay.call(this);
  }, origGetDay);

  Date.prototype.getMonth = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.monthIndex : origGetMonth.call(this);
  }, origGetMonth);

  Date.prototype.getFullYear = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.yearNum : origGetFullYear.call(this);
  }, origGetFullYear);

  Date.prototype.getMinutes = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.minNum : origGetMinutes.call(this);
  }, origGetMinutes);

  Date.prototype.getSeconds = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    return p ? p.secNum : origGetSeconds.call(this);
  }, origGetSeconds);

  Date.prototype.toString = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    if (p) {
      return `${p.weekday} ${p.monthName} ${p.day} ${p.year} ${p.hour}:${p.minute}:${p.second} ${p.gmtString} (${p.tzName})`;
    }
    return origToString.call(this);
  }, origToString);

  Date.prototype.toDateString = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    if (p) {
      return `${p.weekday} ${p.monthName} ${p.day} ${p.year}`;
    }
    return origToDateString.call(this);
  }, origToDateString);

  Date.prototype.toTimeString = makeNative(function() {
    const p = getDateParts(this, active.timeZone);
    if (p) {
      return `${p.hour}:${p.minute}:${p.second} ${p.gmtString} (${p.tzName})`;
    }
    return origToTimeString.call(this);
  }, origToTimeString);

  Date.prototype.toLocaleString = makeNative(function(locales, options) {
    if (Number.isNaN(this.getTime())) return origToLocaleString.call(this, locales, options);
    const opts = options ? Object.assign({}, options) : {
      year: 'numeric', month: 'numeric', day: 'numeric',
      hour: 'numeric', minute: 'numeric', second: 'numeric'
    };
    if (!opts.timeZone) opts.timeZone = active.timeZone;
    const loc = locales || active.locale || 'en-US';
    return new origDTF(loc, opts).format(this);
  }, origToLocaleString);

  Date.prototype.toLocaleDateString = makeNative(function(locales, options) {
    if (Number.isNaN(this.getTime())) return origToLocaleDateString.call(this, locales, options);
    const opts = options ? Object.assign({}, options) : {
      year: 'numeric', month: 'numeric', day: 'numeric'
    };
    if (!opts.timeZone) opts.timeZone = active.timeZone;
    const loc = locales || active.locale || 'en-US';
    return new origDTF(loc, opts).format(this);
  }, origToLocaleDateString);

  Date.prototype.toLocaleTimeString = makeNative(function(locales, options) {
    if (Number.isNaN(this.getTime())) return origToLocaleTimeString.call(this, locales, options);
    const opts = options ? Object.assign({}, options) : {
      hour: 'numeric', minute: 'numeric', second: 'numeric'
    };
    if (!opts.timeZone) opts.timeZone = active.timeZone;
    const loc = locales || active.locale || 'en-US';
    return new origDTF(loc, opts).format(this);
  }, origToLocaleTimeString);

  // Intercept window.Date constructor call without 'new'
  const OrigDate = window.Date;
  function PatchedDate(...args) {
    if (!(this instanceof PatchedDate)) {
      return (new OrigDate()).toString();
    }
    return new OrigDate(...args);
  }
  PatchedDate.prototype = OrigDate.prototype;
  PatchedDate.now = OrigDate.now;
  PatchedDate.parse = OrigDate.parse;
  PatchedDate.UTC = OrigDate.UTC;
  makeNative(PatchedDate, OrigDate, 'Date');
  window.Date = PatchedDate;

  // --- 4. WebRTC, Canvas, WebGL & Audio Prototype Cloaking Helpers ---
  const isLeakingCandidate = (str) => {
    if (!str || typeof str !== 'string') return false;
    if (/typ\s+host/i.test(str)) return true;
    if (/(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|127\.)[0-9]+/.test(str)) return true;
    if (/\bIP6\b/i.test(str)) return true;
    if (/([0-9a-fA-F]{1,4}:){1,7}:|:([0-9a-fA-F]{1,4}:){1,7}|([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::1|fe80:/i.test(str)) return true;
    return false;
  };

  const sanitizeSdp = (sdpStr) => {
    if (!sdpStr || typeof sdpStr !== 'string') return sdpStr;
    const privateIpPattern = /(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|127\.)[0-9.]+/g;
    const ipv6Pattern = /([0-9a-fA-F]{1,4}:){1,7}:|:([0-9a-fA-F]{1,4}:){1,7}|([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::1|fe80:[0-9a-fA-F:]+/gi;
    return sdpStr.split('\r\n').filter(line => {
      if (!line) return false;
      if (line.startsWith('a=candidate:')) {
        if (/typ\s+host/i.test(line)) return false;
        if (/\bIP6\b/i.test(line) || ipv6Pattern.test(line)) return false;
      }
      return true;
    }).map(line => {
      if (line.startsWith('c=IN IP4') || line.startsWith('o=')) {
        line = line.replace(privateIpPattern, '0.0.0.0');
      }
      if (line.startsWith('a=candidate:')) {
        line = line.replace(/raddr\s+[^\s]+/i, 'raddr 0.0.0.0');
      }
      return line;
    }).join('\r\n');
  };

  const patchPCProto = (PC, winRef) => {
    if (!PC || !PC.prototype) return;
    const proto = PC.prototype;
    try {
      const origIceDesc = Object.getOwnPropertyDescriptor(proto, 'onicecandidate');
      if (origIceDesc && origIceDesc.set) {
        Object.defineProperty(proto, 'onicecandidate', {
          get: makeNative(function() {
            return this.__user_ice_handler || origIceDesc.get.call(this);
          }, origIceDesc.get, 'get onicecandidate'),
          set: makeNative(function(fn) {
            if (typeof fn === 'function') {
              const wrapped = function(event) {
                if (event && event.candidate && event.candidate.candidate) {
                  if (isLeakingCandidate(event.candidate.candidate)) return;
                }
                return fn.call(this, event);
              };
              this.__user_ice_handler = fn;
              origIceDesc.set.call(this, wrapped);
            } else {
              this.__user_ice_handler = null;
              origIceDesc.set.call(this, fn);
            }
          }, origIceDesc.set, 'set onicecandidate'),
          configurable: true,
          enumerable: true
        });
      }

      const origAddEventListener = proto.addEventListener;
      if (origAddEventListener) {
        proto.addEventListener = makeNative(function(type, listener, options) {
          if (type === 'icecandidate' && typeof listener === 'function') {
            const wrapped = function(event) {
              if (event && event.candidate && event.candidate.candidate) {
                if (isLeakingCandidate(event.candidate.candidate)) return;
              }
              return listener.call(this, event);
            };
            return origAddEventListener.call(this, type, wrapped, options);
          }
          return origAddEventListener.call(this, type, listener, options);
        }, origAddEventListener, 'addEventListener');
      }

      const origCreateOffer = proto.createOffer;
      if (origCreateOffer) {
        proto.createOffer = makeNative(function(...args) {
          return origCreateOffer.apply(this, args).then(offer => {
            if (offer && offer.sdp) offer.sdp = sanitizeSdp(offer.sdp);
            return offer;
          });
        }, origCreateOffer, 'createOffer');
      }

      const origCreateAnswer = proto.createAnswer;
      if (origCreateAnswer) {
        proto.createAnswer = makeNative(function(...args) {
          return origCreateAnswer.apply(this, args).then(answer => {
            if (answer && answer.sdp) answer.sdp = sanitizeSdp(answer.sdp);
            return answer;
          });
        }, origCreateAnswer, 'createAnswer');
      }

      const origSetLocalDescription = proto.setLocalDescription;
      if (origSetLocalDescription) {
        proto.setLocalDescription = makeNative(function(desc, ...args) {
          if (desc && desc.sdp) {
            desc.sdp = sanitizeSdp(desc.sdp);
          }
          return origSetLocalDescription.call(this, desc, ...args);
        }, origSetLocalDescription, 'setLocalDescription');
      }

      const origLdDesc = Object.getOwnPropertyDescriptor(proto, 'localDescription');
      if (origLdDesc && origLdDesc.get) {
        Object.defineProperty(proto, 'localDescription', {
          get: makeNative(function() {
            const desc = origLdDesc.get.call(this);
            const RTCSD = (winRef && winRef.RTCSessionDescription) || window.RTCSessionDescription;
            if (desc && desc.sdp && RTCSD) {
              return new RTCSD({
                type: desc.type,
                sdp: sanitizeSdp(desc.sdp)
              });
            }
            return desc;
          }, origLdDesc.get, 'get localDescription'),
          configurable: true,
          enumerable: true
        });
      }
    } catch (e) {}
  };

  const patchCanvasRealm = (winRef) => {
    try {
      const CRC2D = winRef.CanvasRenderingContext2D;
      const HCE = winRef.HTMLCanvasElement;
      if (!CRC2D || !CRC2D.prototype) return;
      const origGetImageData = CRC2D.prototype.getImageData;
      if (origGetImageData) {
        CRC2D.prototype.getImageData = makeNative(function(...args) {
          const imageData = origGetImageData.apply(this, args);
          const data = imageData.data;
          for (let i = 0; i < data.length; i += 64) {
            data[i] = Math.min(255, Math.max(0, data[i] + ((i % 3 === 0) ? 1 : -1)));
          }
          return imageData;
        }, origGetImageData, 'getImageData');
      }

      if (HCE && HCE.prototype) {
        const docRef = winRef.document || document;
        const origToDataURL = HCE.prototype.toDataURL;
        if (origToDataURL && origGetImageData) {
          HCE.prototype.toDataURL = makeNative(function(...args) {
            if (this.width <= 16 && this.height <= 16) {
              return origToDataURL.apply(this, args);
            }
            const has2D = (function(c) {
              try { return !!(c.getContext && c.getContext('2d')); } catch (e) { return false; }
            })(this);
            if (!has2D) {
              return origToDataURL.apply(this, args);
            }
            try {
              const offscreen = docRef.createElement('canvas');
              offscreen.width = this.width;
              offscreen.height = this.height;
              const octx = offscreen.getContext('2d');
              if (octx) {
                octx.drawImage(this, 0, 0);
                const imgData = origGetImageData.call(octx, 0, 0, Math.min(4, this.width), Math.min(4, this.height));
                imgData.data[0] = (imgData.data[0] + 1) % 256;
                octx.putImageData(imgData, 0, 0);
                return origToDataURL.apply(offscreen, args);
              }
            } catch (e) {}
            return origToDataURL.apply(this, args);
          }, origToDataURL, 'toDataURL');
        }

        const origToBlob = HCE.prototype.toBlob;
        if (origToBlob && origGetImageData) {
          HCE.prototype.toBlob = makeNative(function(callback, ...args) {
            if (this.width <= 16 && this.height <= 16) {
              return origToBlob.call(this, callback, ...args);
            }
            const has2D = (function(c) {
              try { return !!(c.getContext && c.getContext('2d')); } catch (e) { return false; }
            })(this);
            if (!has2D) {
              return origToBlob.call(this, callback, ...args);
            }
            try {
              const offscreen = docRef.createElement('canvas');
              offscreen.width = this.width;
              offscreen.height = this.height;
              const octx = offscreen.getContext('2d');
              if (octx) {
                octx.drawImage(this, 0, 0);
                const imgData = origGetImageData.call(octx, 0, 0, Math.min(4, this.width), Math.min(4, this.height));
                imgData.data[0] = (imgData.data[0] + 1) % 256;
                octx.putImageData(imgData, 0, 0);
                return origToBlob.call(offscreen, callback, ...args);
              }
            } catch (e) {}
            return origToBlob.call(this, callback, ...args);
          }, origToBlob, 'toBlob');
        }
      }
    } catch (e) {}
  };

  const patchWebGLProto = (proto) => {
    if (!proto || !proto.getParameter) return;
    try {
      const origGetParameter = proto.getParameter;
      proto.getParameter = makeNative(function(pname) {
        if (pname === 0x9245) return 'Apple Inc.';
        if (pname === 0x9246) return 'Apple M2';
        if (pname === 0x1F00) return 'WebKit';
        if (pname === 0x1F01) return 'WebKit WebGL';
        return origGetParameter.call(this, pname);
      }, origGetParameter, 'getParameter');
    } catch (e) {}
  };

  const patchAudioProto = (AB) => {
    if (!AB || !AB.prototype || !AB.prototype.getChannelData) return;
    try {
      const origGetChannelData = AB.prototype.getChannelData;
      AB.prototype.getChannelData = makeNative(function(...args) {
        const channelData = origGetChannelData.apply(this, args);
        for (let i = 0; i < channelData.length; i += 100) {
          channelData[i] += 0.0000001;
        }
        return channelData;
      }, origGetChannelData, 'getChannelData');
    } catch (e) {}
  };

  // --- 5. Prototype-Level Navigator, Client Hints & Synchronous Child Realm Cloaking (v1.5.0) ---
  const patchedRealms = new WeakSet();
  const isClaudeHostGlobal = /claude\.ai|anthropic\.com/i.test(effectiveHost);
  const rootWin = (() => {
    try {
      if (window.top && window.top !== window && window.top.innerWidth) return window.top;
    } catch (e) {}
    return window;
  })();
  const topInnerWDesc = Object.getOwnPropertyDescriptor(rootWin, 'innerWidth');
  const topInnerHDesc = Object.getOwnPropertyDescriptor(rootWin, 'innerHeight');
  const getLockedW = () => {
    const val = topInnerWDesc && topInnerWDesc.get ? topInnerWDesc.get.call(rootWin) : rootWin.innerWidth;
    return (val && val > 320) ? val : 1440;
  };
  const getLockedH = () => {
    const val = topInnerHDesc && topInnerHDesc.get ? topInnerHDesc.get.call(rootWin) : rootWin.innerHeight;
    return (val && val > 240) ? val : 900;
  };

  function patchChildWindowRealm(win) {
    if (!win || (typeof win !== 'object' && typeof win !== 'function')) return;
    try {
      if (patchedRealms.has(win)) return;
      // Access check for same-origin / about:blank realm
      const nav = win.navigator;
      if (!nav) return;
      patchedRealms.add(win);
      try {
        Object.defineProperty(win, INJECT_LOCK, {
          value: true,
          writable: false,
          configurable: false,
          enumerable: false
        });
      } catch (e) {}

      // 1. Stealth Function.prototype.toString in child realm (so R.Function.prototype.toString.call(fn) returns [native code])
      if (win.Function && win.Function.prototype && win.Function.prototype.toString !== Function.prototype.toString) {
        const childOrigToString = win.Function.prototype.toString;
        const wrappedChildToString = function() {
          if (new.target) {
            throw new win.TypeError('Function.prototype.toString is not a constructor');
          }
          if (customToStrings.has(this)) {
            return customToStrings.get(this);
          }
          return childOrigToString.call(this);
        };
        makeNative(wrappedChildToString, childOrigToString, 'toString');
        win.Function.prototype.toString = wrappedChildToString;
      }

      // 2. Patch Navigator.prototype in target realm (covers both o.navigator and o.clientInformation in Cloudflare jsd/oneshot)
      const navProto = (win.Navigator && win.Navigator.prototype)
        ? win.Navigator.prototype
        : Object.getPrototypeOf(nav);

      try {
        if (Object.prototype.hasOwnProperty.call(nav, 'language')) delete nav.language;
        if (Object.prototype.hasOwnProperty.call(nav, 'languages')) delete nav.languages;
      } catch (e) {}

      if (navProto) {
        Object.defineProperty(navProto, 'language', {
          get: makeNative(function() { return active.language; }, null, 'get language'),
          configurable: true,
          enumerable: true
        });

        Object.defineProperty(navProto, 'languages', {
          get: makeNative(function() {
            const arr = win.Array ? win.Array.from(active.languages) : [...active.languages];
            return (win.Object || Object).freeze(arr);
          }, null, 'get languages'),
          configurable: true,
          enumerable: true
        });

        Object.defineProperty(navProto, 'platform', {
          get: makeNative(function() { return 'MacIntel'; }, null, 'get platform'),
          configurable: true,
          enumerable: true
        });

        try {
          Object.defineProperty(navProto, 'webdriver', {
            get: makeNative(function() { return false; }, null, 'get webdriver'),
            configurable: true,
            enumerable: true
          });
        } catch (e) {}

        Object.defineProperty(navProto, 'hardwareConcurrency', {
          get: makeNative(function() { return 8; }, null, 'get hardwareConcurrency'),
          configurable: true,
          enumerable: true
        });

        Object.defineProperty(navProto, 'deviceMemory', {
          get: makeNative(function() { return 8; }, null, 'get deviceMemory'),
          configurable: true,
          enumerable: true
        });
      }

      if (nav.userAgentData && nav.userAgentData.getHighEntropyValues) {
        const origGetHEV = nav.userAgentData.getHighEntropyValues.bind(nav.userAgentData);
        nav.userAgentData.getHighEntropyValues = makeNative(function(hints) {
          return origGetHEV(hints).then(values => {
            if (values.platform) values.platform = 'macOS';
            if (values.architecture) values.architecture = 'arm';
            if (values.bitness) values.bitness = '64';
            if (values.model) values.model = '';
            return values;
          });
        }, origGetHEV, 'getHighEntropyValues');
      }

      // 3. Patch viewport & screen dimensions in target realm (so Cloudflare jsd/oneshot o.outerWidth/outerHeight match main window)
      if (isClaudeHostGlobal) {
        try {
          Object.defineProperty(win, 'outerWidth', {
            get: makeNative(function() { return getLockedW(); }, null, 'get outerWidth'),
            configurable: true,
            enumerable: true
          });
          Object.defineProperty(win, 'outerHeight', {
            get: makeNative(function() { return getLockedH(); }, null, 'get outerHeight'),
            configurable: true,
            enumerable: true
          });
          // NOTE (DeepSeek Consistency Alignment):
          // DO NOT hook Screen.prototype.width/height to equal outerWidth/innerHeight!
          // In real desktop environments, screen.width (e.g. 1512/2560 Retina) > window.innerWidth.
          // Setting them equal triggers Anthropic @ant/o11y's `screen_equals_viewport: true` automation alert!
          // We keep native Screen dimensions untouched to maintain authentic physical entropy.
        } catch (e) {}
      }

      // 4. Patch child realm Date & Intl.DateTimeFormat if distinct from parent window
      if (win !== window) {
        try {
          if (win.Intl) {
            win.Intl.DateTimeFormat = Intl.DateTimeFormat;
          }
          if (win.Date && win.Date.prototype) {
            ['getTimezoneOffset', 'getHours', 'getDate', 'getDay', 'getMonth', 'getFullYear', 'getMinutes', 'getSeconds',
             'toString', 'toDateString', 'toTimeString', 'toLocaleString', 'toLocaleDateString', 'toLocaleTimeString'].forEach((m) => {
              if (Date.prototype[m]) {
                win.Date.prototype[m] = Date.prototype[m];
              }
            });
            const ChildOrigDate = win.Date;
            if (ChildOrigDate !== PatchedDate) {
              function ChildPatchedDate(...args) {
                if (!(this instanceof ChildPatchedDate)) {
                  return (new OrigDate()).toString();
                }
                return new ChildOrigDate(...args);
              }
              ChildPatchedDate.prototype = ChildOrigDate.prototype;
              ChildPatchedDate.now = ChildOrigDate.now || OrigDate.now;
              ChildPatchedDate.parse = ChildOrigDate.parse || OrigDate.parse;
              ChildPatchedDate.UTC = ChildOrigDate.UTC || OrigDate.UTC;
              makeNative(ChildPatchedDate, ChildOrigDate, 'Date');
              win.Date = ChildPatchedDate;
            }
          }
        } catch (e) {}
      }

      // 5. Patch WebRTC, Canvas, WebGL & AudioBuffer in target realm
      if (win.RTCPeerConnection) patchPCProto(win.RTCPeerConnection, win);
      if (win.webkitRTCPeerConnection) patchPCProto(win.webkitRTCPeerConnection, win);
      patchCanvasRealm(win);
      if (win.WebGLRenderingContext) patchWebGLProto(win.WebGLRenderingContext.prototype);
      if (win.WebGL2RenderingContext) patchWebGLProto(win.WebGL2RenderingContext.prototype);
      if (win.AudioBuffer) patchAudioProto(win.AudioBuffer);
    } catch (e) {
      // Cross-origin frame access ignored safely
    }
  }

  try {
    // Apply to main window immediately
    patchChildWindowRealm(window);

    const patchNodeIframes = (node) => {
      try {
        if (node && typeof node === 'object') {
          if (node.tagName === 'IFRAME' && node.contentWindow) {
            patchChildWindowRealm(node.contentWindow);
          } else if (node.querySelectorAll) {
            const frames = node.querySelectorAll('iframe');
            for (let i = 0; i < frames.length; i++) {
              if (frames[i].contentWindow) patchChildWindowRealm(frames[i].contentWindow);
            }
          }
        }
        if (document && document.getElementsByTagName) {
          const allIframes = document.getElementsByTagName('iframe');
          for (let i = 0; i < allIframes.length; i++) {
            if (allIframes[i].contentWindow) patchChildWindowRealm(allIframes[i].contentWindow);
          }
        }
        if (window.frames && typeof window.frames.length === 'number') {
          for (let i = 0; i < window.frames.length; i++) {
            patchChildWindowRealm(window.frames[i]);
          }
        }
      } catch (e) {}
    };

    // Hook HTMLIFrameElement.prototype.contentWindow & contentDocument getters so synchronous about:blank iframe probes
    // (e.g., Cloudflare jsd/main.js function B(): R = createElement('iframe'); body.appendChild(R); o = R.contentWindow)
    // receive a fully cloaked realm on the spot before a single property can be read!
    if (typeof HTMLIFrameElement !== 'undefined' && HTMLIFrameElement.prototype) {
      const origCWDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
      const origCDDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentDocument');

      if (origCWDesc && origCWDesc.get) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
          get: makeNative(function() {
            const cw = origCWDesc.get.call(this);
            if (cw) {
              try { patchChildWindowRealm(cw); } catch (e) {}
            }
            return cw;
          }, origCWDesc.get, 'get contentWindow'),
          configurable: true,
          enumerable: true
        });
      }

      if (origCDDesc && origCDDesc.get) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentDocument', {
          get: makeNative(function() {
            const cd = origCDDesc.get.call(this);
            try {
              const cw = origCWDesc && origCWDesc.get ? origCWDesc.get.call(this) : (cd && cd.defaultView);
              if (cw) patchChildWindowRealm(cw);
            } catch (e) {}
            return cd;
          }, origCDDesc.get, 'get contentDocument'),
          configurable: true,
          enumerable: true
        });
      }
    }

    // Hook all synchronous DOM insertion & HTML parsing methods so iframes accessed via window.frames[i] are already cloaked
    if (typeof Node !== 'undefined' && Node.prototype) {
      ['appendChild', 'insertBefore', 'replaceChild'].forEach((method) => {
        const orig = Node.prototype[method];
        if (orig) {
          Node.prototype[method] = makeNative(function(...args) {
            const res = orig.apply(this, args);
            patchNodeIframes(args[0]);
            return res;
          }, orig, method);
        }
      });
    }

    if (typeof Element !== 'undefined' && Element.prototype) {
      ['append', 'prepend', 'after', 'before', 'replaceWith', 'insertAdjacentElement', 'insertAdjacentHTML'].forEach((method) => {
        const orig = Element.prototype[method];
        if (orig) {
          Element.prototype[method] = makeNative(function(...args) {
            const res = orig.apply(this, args);
            for (let i = 0; i < args.length; i++) {
              if (args[i] && typeof args[i] === 'object') patchNodeIframes(args[i]);
            }
            patchNodeIframes(this);
            return res;
          }, orig, method);
        }
      });

      ['innerHTML', 'outerHTML'].forEach((prop) => {
        const desc = Object.getOwnPropertyDescriptor(Element.prototype, prop);
        if (desc && desc.set) {
          Object.defineProperty(Element.prototype, prop, {
            get: desc.get,
            set: makeNative(function(val) {
              const res = desc.set.call(this, val);
              if (typeof val === 'string' && /<iframe/i.test(val)) {
                patchNodeIframes(this);
              }
              return res;
            }, desc.set, `set ${prop}`),
            configurable: true,
            enumerable: true
          });
        }
      });
    }

    if (typeof Range !== 'undefined' && Range.prototype && Range.prototype.insertNode) {
      const origInsertNode = Range.prototype.insertNode;
      Range.prototype.insertNode = makeNative(function(node, ...rest) {
        const res = origInsertNode.call(this, node, ...rest);
        patchNodeIframes(node);
        return res;
      }, origInsertNode, 'insertNode');
    }

    if (typeof Document !== 'undefined' && Document.prototype) {
      ['write', 'writeln'].forEach((method) => {
        const orig = Document.prototype[method];
        if (orig) {
          Document.prototype[method] = makeNative(function(...args) {
            const res = orig.apply(this, args);
            patchNodeIframes(this);
            return res;
          }, orig, method);
        }
      });
    }
  } catch (e) {
    console.debug('[ClaudeShield] Navigator & child realm cloak error:', e);
  }

  // --- 9. Referrer & Tracking Token Sanitization ---
  try {
    const rawReferrer = document.referrer || '';
    const isClaude = isClaudeHostGlobal;
    const domesticMailRegex = /(mail\.163\.com|mail\.qq\.com|mail\.126\.com|mail\.sina\.com|mail\.aliyun\.com|exmail\.qq\.com|qiye\.aliyun\.com)/i;
    if (isClaude && (domesticMailRegex.test(rawReferrer) || (rawReferrer && !rawReferrer.includes('anthropic.com') && !rawReferrer.includes('claude.ai')))) {
      Object.defineProperty(document, 'referrer', {
        get: makeNative(function() { return 'https://claude.ai/'; }, null, 'get referrer'),
        configurable: true
      });
    }

    // Only strip tracking parameters on Claude.ai to avoid breaking query params on test sites (e.g. ?source=claude-subscribe on bewild.ai)
    if (isClaude && window.location && /^https?:/i.test(window.location.href)) {
      const url = new URL(window.location.href);
      const trackingKeys = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'mc_cid', 'mc_eid', '_hsenc', '_hsmi', 'tracking_id',
        'msclkid', 'twclid', 'wickedid', '_openstat', 'yclid', 'dclid', 'zanpid',
        'igshid', 'ref', 'referrer', 'source'
      ];
      let cleaned = false;
      trackingKeys.forEach(k => {
        if (url.searchParams.has(k)) {
          url.searchParams.delete(k);
          cleaned = true;
        }
      });
      if (cleaned && window.history && window.history.replaceState) {
        window.history.replaceState(null, '', url.pathname + url.search + url.hash);
        console.log('[ClaudeShield] Stripped tracking tokens from magic link / URL.');
      }
    }
  } catch (e) {
    console.debug('[ClaudeShield] Tracker sanitizer error:', e);
  }

  // --- 10. RUM Worker Sanitization, dcz=keep Defense & Account Standing Inspector (v1.5.0) ---
  try {
    if (isClaudeHostGlobal) {
      // 10.1 Deep sanitize raw Datadog RUM JSON events BEFORE ant-rum-worker / Datadog deflate worker compresses them
      const sanitizeRumEventLine = (lineStr) => {
        if (!lineStr || typeof lineStr !== 'string') return lineStr;
        try {
          const ev = JSON.parse(lineStr);
          if (!ev || typeof ev !== 'object') return lineStr;

          // Sanitize context properties injected by wJ() / Y4() / CM()
          if (ev.context && typeof ev.context === 'object') {
            ev.context.screen_equals_viewport = true;
            ev.context.is_automation = false;
            delete ev.context.automation_signal;
            ev.context.hidden_at_load = false;
            ev.context.had_focus = true;
            ev.context.ua_client_hints = 'match';
            ev.context.ua_form = 'reduced';
            ev.context.client_tz = active.timeZone || 'Asia/Taipei';
            ev.context.ui_locale = active.locale || 'zh-TW';
            if (typeof ev.context.added_extension_url_count === 'number') {
              ev.context.added_extension_url_count = 0;
            }
            if (typeof ev.context.added_resource_schemes === 'string') {
              ev.context.added_resource_schemes = ev.context.added_resource_schemes
                .split(',')
                .filter(s => !/extension/i.test(s))
                .join(',');
            }
          }

          // Sanitize view referrer & URL
          if (ev.view && typeof ev.view === 'object') {
            if (ev.view.referrer && !ev.view.referrer.includes('claude.ai')) {
              ev.view.referrer = 'https://claude.ai/';
            }
          }

          // Neutralize extension detection event if ever triggered
          if (ev.action && ev.action.target && ev.action.target.name === 'app.document_gutted') {
            ev.action.target.name = 'page.content_ready';
          }

          return JSON.stringify(ev);
        } catch (e) {
          return lineStr;
        }
      };

      const sanitizeRumMultiLine = (chunkStr) => {
        if (!chunkStr || typeof chunkStr !== 'string') return chunkStr;
        return chunkStr.split('\n').map(sanitizeRumEventLine).join('\n');
      };

      // Hook Worker.prototype.postMessage so both Anthropic ant-rum-worker (t:'scrub' / t:'deflate')
      // and Datadog Browser SDK deflate worker (action:'write', data:'...') receive sanitized events
      if (window.Worker && window.Worker.prototype && window.Worker.prototype.postMessage) {
        const origPostMessage = window.Worker.prototype.postMessage;
        window.Worker.prototype.postMessage = makeNative(function(message, ...transfer) {
          try {
            if (typeof message === 'string') {
              message = sanitizeRumMultiLine(message);
            } else if (message && typeof message === 'object') {
              if (message.t === 'scrub' && Array.isArray(message.items)) {
                message = Object.assign({}, message, {
                  items: message.items.map(item => {
                    if (item && typeof item.data === 'string') {
                      return Object.assign({}, item, { data: sanitizeRumMultiLine(item.data) });
                    }
                    return item;
                  })
                });
              } else if (typeof message.text === 'string') {
                message = Object.assign({}, message, {
                  text: sanitizeRumMultiLine(message.text)
                });
              } else if (typeof message.data === 'string') {
                message = Object.assign({}, message, {
                  data: sanitizeRumMultiLine(message.data)
                });
              }
            }
          } catch (e) {}
          return origPostMessage.call(this, message, ...transfer);
        }, origPostMessage, 'postMessage');
      }

      // 10.2 Sanitize & simulate natural human telemetry in /api/event_logging/v2/batch (1st-party JSON)
      const sanitizeEventBatch = (bodyStr) => {
        if (typeof bodyStr !== 'string' || !bodyStr.includes('events')) return bodyStr;
        try {
          const data = JSON.parse(bodyStr);
          if (data && Array.isArray(data.events)) {
            data.events = data.events.filter((ev) => {
              const actionName = ev && ev.event_data && (ev.event_data.action || ev.event_data.event_name);
              // Drop extension DOM tampering alerts if any
              return actionName !== 'app.document_gutted' && actionName !== 'app.rum_intake_fallback';
            });
            data.events.forEach((ev) => {
              if (!ev || !ev.event_data) return;
              const ed = ev.event_data;
              // Force screen_equals_viewport = true & is_automation = false
              if (typeof ed.screen_equals_viewport === 'boolean') {
                ed.screen_equals_viewport = true;
              }
              if (typeof ed.is_automation === 'boolean') {
                ed.is_automation = false;
              }
              // Simulate natural human typing in claudeai.perf.interaction_histogram
              if (ed.event_name === 'claudeai.perf.interaction_histogram' && typeof ed.properties === 'string') {
                try {
                  const props = JSON.parse(ed.properties);
                  if (Array.isArray(props.key_paste_non_nav)) {
                    props.key_paste_non_nav = [0, 0, 0, 0];
                  }
                  const sumKey = Array.isArray(props.key_non_nav) ? props.key_non_nav.reduce((a, b) => a + b, 0) : 0;
                  if (sumKey === 0) {
                    const b0 = 8 + Math.floor(Math.random() * 14);
                    const b1 = 4 + Math.floor(Math.random() * 8);
                    const b2 = 1 + Math.floor(Math.random() * 4);
                    props.key_non_nav = [b0, b1, b2, 0];
                    const p0 = 2 + Math.floor(Math.random() * 5);
                    const p1 = 1 + Math.floor(Math.random() * 3);
                    props.pointer_non_nav = [p0, p1, 0, 0];
                    props.total_interactions = Math.max(props.total_interactions || 0, b0 + b1 + b2 + p0 + p1 + 12);
                  }
                  if (typeof props.hidden_excluded === 'number') {
                    props.hidden_excluded = 0;
                  }
                  ed.properties = JSON.stringify(props);
                } catch (pe) {}
              }
            });
            return JSON.stringify(data);
          }
        } catch (e) {}
        return bodyStr;
      };

      // 10.3 Strip dcz=keep compression dictionary tracking from Accept headers (HAR-3 [00..15])
      const cleanAcceptDcz = (val) => {
        if (typeof val !== 'string' || !/dcz=keep/i.test(val)) return val;
        return val.replace(/[;,]?\s*dcz=keep/gi, '').replace(/^[,;\s]+|[,;\s]+$/g, '').trim() || '*/*';
      };

      const stripDczFromHeaders = (headers) => {
        if (!headers) return headers;
        try {
          if (typeof Headers !== 'undefined' && headers instanceof Headers) {
            const acc = headers.get('accept') || headers.get('Accept');
            if (acc && /dcz=keep/i.test(acc)) {
              const cloned = new Headers(headers);
              cloned.set('accept', cleanAcceptDcz(acc));
              return cloned;
            }
          } else if (Array.isArray(headers)) {
            return headers.map(([k, v]) => {
              if (typeof k === 'string' && k.toLowerCase() === 'accept' && typeof v === 'string' && /dcz=keep/i.test(v)) {
                return [k, cleanAcceptDcz(v)];
              }
              return [k, v];
            });
          } else if (typeof headers === 'object') {
            const out = Object.assign({}, headers);
            Object.keys(out).forEach((k) => {
              if (k.toLowerCase() === 'accept' && typeof out[k] === 'string' && /dcz=keep/i.test(out[k])) {
                out[k] = cleanAcceptDcz(out[k]);
              }
            });
            return out;
          }
        } catch (e) {}
        return headers;
      };

      if (window.XMLHttpRequest && window.XMLHttpRequest.prototype && window.XMLHttpRequest.prototype.setRequestHeader) {
        const origSetReqHeader = window.XMLHttpRequest.prototype.setRequestHeader;
        window.XMLHttpRequest.prototype.setRequestHeader = makeNative(function(header, value) {
          if (typeof header === 'string' && header.toLowerCase() === 'accept' && typeof value === 'string' && /dcz=keep/i.test(value)) {
            value = cleanAcceptDcz(value);
          }
          return origSetReqHeader.call(this, header, value);
        }, origSetReqHeader, 'setRequestHeader');
      }

      // 10.4 Account Standing, Ban Reason, Appeal Status & KYC Inspector (HAR-1 [007, 149, 179, 203] & HAR-2 [008, 147, 200, 201])
      const STANDING_EVENT_NAME = '__CLAUDE_SHIELD_ACCOUNT_STANDING__';
      const PROBE_TRIGGER_EVENT = '__CLAUDE_SHIELD_PROBE_STANDING__';
      // Start with an empty object so partial endpoint updates never overwrite previously cached fields with null
      const standingReport = {};

      const emitStandingUpdate = (patch) => {
        try {
          if (patch && typeof patch === 'object') {
            Object.assign(standingReport, patch, { updatedAt: Date.now() });
          }
          const detailObj = JSON.parse(JSON.stringify(standingReport));
          document.dispatchEvent(new CustomEvent(STANDING_EVENT_NAME, { detail: detailObj }));
        } catch (e) {}
      };

      const inspectStandingResponse = (urlStr, res, reqInit) => {
        if (!urlStr || !res || typeof res.clone !== 'function') return Promise.resolve();
        try {
          // 1. GET /api/account/standing
          if (urlStr.includes('/api/account/standing')) {
            return res.clone().json().then((d) => {
              if (d && typeof d === 'object') {
                const patch = {
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
                  reinstatement_credit_cents: d.reinstatement_credit_cents ?? null,
                  standingHttpStatus: res.status
                };
                emitStandingUpdate(patch);
              }
            }).catch(() => {});
          }

          // 2. GET /api/account/current_appeal or POST /api/account/appeal
          if (urlStr.includes('/api/account/current_appeal') || urlStr.includes('/api/account/appeal')) {
            let postedQuestionnaire = null;
            if (reqInit && typeof reqInit.body === 'string') {
              try {
                const parsedReq = JSON.parse(reqInit.body);
                postedQuestionnaire = (parsedReq && parsedReq.questionnaire) || parsedReq || null;
              } catch (e) {}
            }
            return res.clone().json().then((d) => {
              if (d === null) {
                emitStandingUpdate({
                  appeal: { status: null, created_at: null, questionnaire: null }
                });
              } else if (d && typeof d === 'object') {
                const apObj = (d.appeal && typeof d.appeal === 'object') ? d.appeal : d;
                emitStandingUpdate({
                  appeal: {
                    status: apObj.status || 'open',
                    created_at: apObj.created_at || new Date().toISOString(),
                    questionnaire: apObj.questionnaire || postedQuestionnaire || null
                  }
                });
              }
            }).catch(() => {});
          }

          // 3. GET /api/account/deletion-allowed
          if (urlStr.includes('/api/account/deletion-allowed')) {
            return res.clone().json().then((d) => {
              if (d && typeof d === 'object') {
                const isDeletable = typeof d.deletable === 'boolean' ? d.deletable : Boolean(d.allowed);
                emitStandingUpdate({
                  deletion: {
                    deletable: isDeletable,
                    allowed: isDeletable,
                    reasons: Array.isArray(d.reasons) ? d.reasons : [],
                    display_message: d.display_message || null
                  }
                });
              }
            }).catch(() => {});
          }

          // 4. GET /edge-api/bootstrap/.../app_start or /api/bootstrap
          if (urlStr.includes('/app_start') || urlStr.includes('/api/bootstrap') || urlStr.includes('/edge-api/bootstrap')) {
            const orgMatch = urlStr.match(/\/bootstrap\/([0-9a-f-]{36})\/app_start/i);
            const orgUuid = orgMatch ? orgMatch[1] : null;
            return res.clone().json().then((d) => {
              if (res.status === 403 && d && d.error) {
                const errCode = (d.error.details && d.error.details.error_code) || d.error.message || 'account_banned';
                const patch = {
                  bootstrap: {
                    status: 403,
                    error_code: errCode,
                    appeals_redirect_enabled: Boolean(d.error.details && d.error.details.appeals_redirect_enabled),
                    request_id: d.request_id || null,
                    org_uuid: orgUuid
                  }
                };
                if (!standingReport.standing) {
                  patch.standing = errCode === 'account_banned' ? 'bad_standing' : 'restricted';
                }
                emitStandingUpdate(patch);
              } else if (res.status === 200 && d && typeof d === 'object') {
                const patch = {
                  bootstrap: {
                    status: 200,
                    error_code: null,
                    account_email: (d.account && d.account.email_address) || null,
                    account_uuid: (d.account && d.account.uuid) || null,
                    org_uuid: orgUuid
                  }
                };
                if (!standingReport.standing || standingReport.standing !== 'bad_standing') {
                  patch.standing = 'good_standing';
                  patch.ban_category = null;
                  patch.banned_at = null;
                  patch.banned_orgs = [];
                }
                emitStandingUpdate(patch);
              }
            }).catch(() => {});
          }

          // 5. GET /api/organizations/.../kyc_status
          if (urlStr.includes('/kyc_status')) {
            const orgMatch = urlStr.match(/\/organizations\/([^/?]+)\/kyc_status/i);
            const orgUuid = orgMatch ? orgMatch[1] : null;
            return res.clone().json().then((d) => {
              if (d && typeof d === 'object') {
                emitStandingUpdate({
                  kyc: {
                    status: d.status || 'unknown',
                    can_retry: d.can_retry ?? null,
                    should_poll: d.should_poll ?? null,
                    org_uuid: orgUuid
                  }
                });
              }
            }).catch(() => {});
          }
        } catch (e) {}
        return Promise.resolve();
      };

      // Intercept window.fetch for:
      // 1) /api/event_logging/v2/batch scrubbing
      // 2) 1st-party & 3rd-party /api/v2/rum string fallback scrubbing (binary deflate streams from Worker pass through natively)
      // 3) dcz=keep Accept header stripping (HAR-3)
      // 4) Passive response inspection for Account Standing / Appeal / Deletion / Bootstrap / KYC
      const origFetch = window.fetch;
      if (origFetch) {
        window.fetch = makeNative(function(input, init) {
          let urlStr = '';
          try {
            if (typeof input === 'string') {
              urlStr = input;
            } else if (input && typeof input === 'object') {
              urlStr = typeof input.url === 'string'
                ? input.url
                : (typeof input.href === 'string' ? input.href : String(input));
            }
            if (init && init.headers) {
              init = Object.assign({}, init, { headers: stripDczFromHeaders(init.headers) });
            } else if (typeof Request !== 'undefined' && input instanceof Request && input.headers) {
              const acc = input.headers.get('accept') || '';
              if (/dcz=keep/i.test(acc)) {
                const newHeaders = stripDczFromHeaders(input.headers);
                input = new Request(input, { headers: newHeaders });
              }
            }
            if (urlStr.includes('/api/event_logging/v2/batch') && init && typeof init.body === 'string') {
              init = Object.assign({}, init, { body: sanitizeEventBatch(init.body) });
            } else if (urlStr.includes('/api/v2/rum') && init && typeof init.body === 'string') {
              init = Object.assign({}, init, { body: sanitizeRumMultiLine(init.body) });
            }
          } catch (e) {}

          const fetchPromise = origFetch.call(this, input, init);
          if (urlStr && (
            urlStr.includes('/api/account/standing') ||
            urlStr.includes('/api/account/current_appeal') ||
            urlStr.includes('/api/account/appeal') ||
            urlStr.includes('/api/account/deletion-allowed') ||
            urlStr.includes('/app_start') ||
            urlStr.includes('/api/bootstrap') ||
            urlStr.includes('/edge-api/bootstrap') ||
            urlStr.includes('/kyc_status')
          )) {
            fetchPromise.then((res) => {
              inspectStandingResponse(urlStr, res, init);
            }).catch(() => {});
          }
          return fetchPromise;
        }, origFetch, 'fetch');

        // Active standing probe listener triggered by popup -> content.js
        if (!window.top || window === window.top) {
          document.addEventListener(PROBE_TRIGGER_EVENT, () => {
            try {
              const fetchOpts = {
                method: 'GET',
                credentials: 'include',
                headers: { 'Accept': 'application/json' },
                cache: 'no-store'
              };
              Promise.allSettled([
                origFetch.call(window, '/api/account/standing', fetchOpts)
                  .then(r => inspectStandingResponse('/api/account/standing', r)),
                origFetch.call(window, '/api/account/current_appeal', fetchOpts)
                  .then(r => inspectStandingResponse('/api/account/current_appeal', r)),
                origFetch.call(window, '/api/account/deletion-allowed', fetchOpts)
                  .then(r => inspectStandingResponse('/api/account/deletion-allowed', r))
              ]).then(() => {
                emitStandingUpdate({ source: 'active_main_probe' });
              });
            } catch (e) {}
          });
        }
      }

      // Intercept navigator.sendBeacon to sanitize /api/event_logging/v2/batch and plain-text /api/v2/rum on page unload
      if (navigator.sendBeacon) {
        const origSendBeacon = navigator.sendBeacon;
        navigator.sendBeacon = makeNative(function(url, data) {
          try {
            const urlStr = String(url || '');
            if (urlStr.includes('/api/event_logging/v2/batch') && typeof data === 'string') {
              data = sanitizeEventBatch(data);
            } else if (urlStr.includes('/api/v2/rum') && typeof data === 'string') {
              data = sanitizeRumMultiLine(data);
            }
          } catch (e) {}
          return origSendBeacon.call(this, url, data);
        }, origSendBeacon, 'sendBeacon');
      }
    }
  } catch (e) {
    console.debug('[ClaudeShield] Telemetry cloak error:', e);
  }

  console.log(`[ClaudeShield v1.5.0] Initialized: ${active.name} | TZ: ${active.timeZone} | Lang: ${active.language}`);
})();
