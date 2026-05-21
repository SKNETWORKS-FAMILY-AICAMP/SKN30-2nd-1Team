/* ============================================
   튜브어때 발표 슬라이드 - 네비게이션
   슬라이드 추가/순서 변경은 SLIDES 배열만 수정
   ============================================ */

const SLIDES = [
  { file: '01-title.html',                 title: '타이틀' },
  { file: '02-team.html',                  title: '팀 소개' },
  { file: '03-project-overview.html',      title: '프로젝트 개요' },
  { file: '04-problem-definition.html',    title: '문제 정의' },
  { file: '04-selection-background.html',  title: '선정 배경' },
  { file: '04-project-goal.html',         title: '프로젝트 목표' },
  { file: '04-expected-effect.html',      title: '기대 효과' },
  { file: '05-roles.html',                 title: '역할 분담 / WBS' },
  { file: '06-core-features.html',         title: '핵심 기능' },
  { file: '07-data-flow.html',             title: '데이터 흐름' },
  { file: '08-tech-stack.html',            title: '사용한 기술 스택' },
  { file: '09-dataset.html',               title: '사용한 데이터' },
  { file: '10-eda.html',                   title: 'EDA' },
  { file: '11-data-preprocessing.html',    title: '데이터 전처리 결과' },
  { file: '12-erd.html',                   title: 'ERD 구조도' },
  { file: '13-model-results.html',         title: '모델 결과 (학습 결과서)' },
  { file: '14-model-selection.html',       title: '모델 선정 이유' },
  { file: '15-insights.html',              title: '분석 결과 인사이트' },
  { file: '16-sitemap.html',               title: '사이트맵 / 화면 설계' },
  { file: '17-screen-demo.html',           title: '화면 시연 (라이브)' },
  { file: '17-demo-fullscreen.html',       title: '라이브 데모 전체 화면' },
  { file: '18-utilization.html',           title: '활용 가능성' },
  { file: '19-results-retrospective.html', title: '프로젝트 결과 / 회고' },
  { file: '20-references.html',            title: '참고 자료' },
];

const state = {
  index: 0,
  slideNodes: [],
  observer: null,
};

function formatSlideLabel(index) {
  const slide = SLIDES[index];
  const num = String(index + 1).padStart(2, '0');
  return `${num}. ${slide.title}`;
}

async function renderAllSlides() {
  const stage = document.getElementById('stage');
  stage.innerHTML = '';
  state.slideNodes = [];
  document.documentElement.style.setProperty('--slide-total', SLIDES.length);

  for (let i = 0; i < SLIDES.length; i++) {
    const slide = SLIDES[i];
    let html;
    try {
      const res = await fetch(`slides/${slide.file}?v=${Date.now()}`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${res.status}`);
      html = await res.text();
    } catch (e) {
      html = `<div class="slide"><h2 class="slide-title">슬라이드 로딩 실패</h2>
              <p class="muted">${slide.file} — ${e.message}</p>
              <p class="small">⚠️ <code>file://</code> 로 열었다면 <code>python -m http.server</code> 등으로 로컬 서버를 띄워주세요.</p>
              </div>`;
    }

    const wrap = document.createElement('div');
    wrap.className = 'slide-stage';
    wrap.innerHTML = html;
    executeEmbeddedScripts(wrap);
    const footerLabel = wrap.querySelector('.slide-footer > span:first-child');
    if (footerLabel && i > 0) {
      footerLabel.textContent = formatSlideLabel(i);
    }
    stage.appendChild(wrap);
    state.slideNodes.push(wrap);
    attachDemoFallback(wrap);
  }

  observeSlides();
  updateNav();
  updateUrlHash();
}

function updateNav() {
  document.getElementById('nav-num').textContent =
    `${state.index + 1} / ${SLIDES.length}`;
  const sel = document.getElementById('jump');
  if (sel) sel.value = state.index;
}

function updateUrlHash() {
  const hash = `#${state.index + 1}`;
  if (location.hash !== hash) history.replaceState(null, '', hash);
}

function executeEmbeddedScripts(container) {
  const scripts = Array.from(container.querySelectorAll('script'));
  for (const oldScript of scripts) {
    const newScript = document.createElement('script');
    for (const attr of oldScript.attributes) {
      newScript.setAttribute(attr.name, attr.value);
    }
    newScript.text = oldScript.textContent;
    oldScript.replaceWith(newScript);
  }
}

function scrollToSlide(i) {
  if (i < 0 || i >= state.slideNodes.length) return;
  state.index = i;
  updateNav();
  updateUrlHash();
  state.slideNodes[i].scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function next() { scrollToSlide(Math.min(SLIDES.length - 1, state.index + 1)); }
function prev() { scrollToSlide(Math.max(0, state.index - 1)); }

function observeSlides() {
  if (state.observer) state.observer.disconnect();

  state.observer = new IntersectionObserver((entries) => {
    let best = null;
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      if (!best || entry.intersectionRatio > best.intersectionRatio) {
        best = entry;
      }
    }
    if (!best) return;
    const index = state.slideNodes.indexOf(best.target);
    if (index >= 0 && index !== state.index) {
      state.index = index;
      updateNav();
      updateUrlHash();
    }
  }, {
    threshold: [0.35, 0.5, 0.65, 0.8],
    root: null,
  });

  state.slideNodes.forEach((node) => state.observer.observe(node));
}

/* iframe 로드 실패 시 fallback 표시 */
function attachDemoFallback(stage) {
  const frame = stage.querySelector('.demo-frame iframe');
  if (!frame) return;
  const wrapper = frame.closest('.demo-frame');
  let loaded = false;
  const fail = () => { if (!loaded) wrapper.classList.add('failed'); };
  const ok = () => { loaded = true; };
  frame.addEventListener('load', ok);
  frame.addEventListener('error', fail);
  // Streamlit이 안 떠있으면 onload 자체가 안 일어남 → 4초 타임아웃
  setTimeout(fail, 4000);
}

/* 키보드 이벤트 */
document.addEventListener('keydown', (e) => {
  // 입력 필드에서는 무시
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
    e.preventDefault(); next();
  } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
    e.preventDefault(); prev();
  } else if (e.key === 'Home') {
    e.preventDefault(); scrollToSlide(0);
  } else if (e.key === 'End') {
    e.preventDefault(); scrollToSlide(SLIDES.length - 1);
  } else if (e.key === 'p' || e.key === 'P') {
    e.preventDefault(); togglePrintMode();
  }
});

/* 인쇄 모드 토글 */
function togglePrintMode() {
  document.body.classList.toggle('print-mode');
  if (document.body.classList.contains('print-mode')) {
    renderAllSlides();
  } else {
    renderAllSlides().then(() => {
      if (state.slideNodes[state.index]) {
        state.slideNodes[state.index].scrollIntoView({ block: 'start' });
      }
    });
  }
}

/* 초기화 */
window.addEventListener('DOMContentLoaded', () => {
  // 드롭다운 채우기
  const sel = document.getElementById('jump');
  SLIDES.forEach((s, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = formatSlideLabel(i);
    sel.appendChild(opt);
  });
  sel.addEventListener('change', (e) => scrollToSlide(parseInt(e.target.value, 10)));

  document.getElementById('btn-prev').addEventListener('click', prev);
  document.getElementById('btn-next').addEventListener('click', next);

  // URL hash로 시작 슬라이드 결정
  const hashNum = parseInt((location.hash || '#1').slice(1), 10);
  const start = Number.isFinite(hashNum) && hashNum >= 1 && hashNum <= SLIDES.length
    ? hashNum - 1 : 0;

  // ?print=true 면 인쇄 모드
  if (new URLSearchParams(location.search).get('print') === 'true') {
    document.body.classList.add('print-mode');
    renderAllSlides();
  } else {
    renderAllSlides().then(() => {
      state.index = start;
      updateNav();
      updateUrlHash();
      if (state.slideNodes[start]) {
        state.slideNodes[start].scrollIntoView({ block: 'start' });
      }
    });
  }
});
