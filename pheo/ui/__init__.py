PREFERENCE_STORE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PHEO Local Apprentice</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --green: #0d6f5b;
      --green-soft: #edf7f4;
      --blue: #1a73e8;
      --blue-soft: #e8f0fe;
      --amber: #b06000;
      --amber-soft: #fef7e0;
      --paper: rgba(255,255,255,.96);
      --soft: #f8fafd;
      --grid: rgba(32,33,36,.026);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 "Google Sans", "Inter", Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        linear-gradient(var(--grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--grid) 1px, transparent 1px),
        #f3f7f5;
      background-size: 32px 32px;
    }
    header {
      padding: 16px 28px;
      background: rgba(255,255,255,.94);
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 18px;
    }
    h1 { margin: 0; font-size: 28px; font-weight: 600; letter-spacing: 0; line-height: 1; cursor: pointer; }
    h2 { margin: 0 0 8px; font-size: 18px; font-weight: 600; letter-spacing: 0; }
    h3 { margin: 0 0 8px; font-size: 14px; font-weight: 600; letter-spacing: 0; }
    p { margin: 0; }
    main { padding: 24px 28px 42px; }
    button, input, textarea, select { font: inherit; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: white;
      color: var(--ink);
    }
    textarea { min-height: 110px; resize: vertical; }
    label { display: block; margin: 12px 0 6px; color: var(--muted); font-size: 12px; font-weight: 600; }
    button {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      color: var(--ink);
      padding: 8px 11px;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { border-color: #b7c9c4; }
    button:disabled { opacity: .55; cursor: default; border-color: var(--line); }
    button.primary { background: var(--green); border-color: var(--green); color: white; }
    button.blue { background: var(--blue-soft); border-color: #b8d4e2; color: var(--blue); }
    button.amber { background: var(--amber-soft); border-color: #e3c897; color: #7a561f; }
    button.ghost { background: transparent; }
    button.nowrap { white-space: nowrap; }
    button.step {
      text-align: left;
      width: 100%;
      display: grid;
      grid-template-columns: 34px 1fr;
      gap: 10px;
      align-items: center;
      padding: 12px;
    }
    button.step.active { border-color: var(--green); background: var(--green-soft); }
    button.step.locked { opacity: .45; cursor: default; }
    .muted { color: var(--muted); }
    .shell {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .card {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 10px;
      box-shadow: 0 1px 2px rgba(60,64,67,.08);
    }
    .pad { padding: 20px; }
    .welcome {
      max-width: 1280px;
      margin: 18px auto;
      display: grid;
      grid-template-columns: 304px minmax(0, 1fr);
      gap: 18px;
      align-items: stretch;
    }
    .welcome-nav { padding: 16px; min-height: 560px; }
    .welcome-main {
      padding: 30px 34px;
      min-height: 560px;
      background:
        radial-gradient(circle at 88% 12%, rgba(232,240,254,.88), transparent 30%),
        radial-gradient(circle at 8% 4%, rgba(237,247,244,.88), transparent 26%),
        var(--paper);
    }
    .nav-section { margin-top: 22px; }
    .nav-section-title {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      margin: 0 0 10px;
    }
    .nav-link {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      border: 0;
      background: transparent;
      padding: 9px 10px;
      border-radius: 999px;
      text-align: left;
      font-weight: 500;
    }
    .nav-link:hover { background: var(--soft); border-color: transparent; }
    .home-prompt {
      min-height: 230px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      border-bottom: 1px solid var(--line);
      margin-bottom: 24px;
      padding-bottom: 26px;
    }
    .flywheel-card {
      margin-top: 22px;
      max-width: 860px;
      display: grid;
      grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
      gap: 18px;
      align-items: center;
      padding: 16px;
      border: 1px solid rgba(176,96,0,.18);
      border-radius: 14px;
      background:
        radial-gradient(circle at 12% 16%, rgba(254,247,224,.95), transparent 36%),
        radial-gradient(circle at 82% 70%, rgba(232,240,254,.8), transparent 36%),
        rgba(255,255,255,.78);
    }
    .flywheel-orbit {
      position: relative;
      aspect-ratio: 1;
      min-height: 220px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: radial-gradient(circle, rgba(255,255,255,.96) 0 35%, rgba(254,247,224,.68) 36% 48%, transparent 49%);
    }
    .orbit-line {
      position: absolute;
      inset: 22px;
      border: 1px solid rgba(176,96,0,.24);
      border-radius: 999px;
    }
    .orbit-line::after {
      content: "";
      position: absolute;
      inset: -3px;
      border-radius: inherit;
      border: 3px solid transparent;
      border-top-color: rgba(176,96,0,.72);
      border-right-color: rgba(26,115,232,.42);
      animation: spin 7.5s linear infinite;
    }
    .orbit-core {
      z-index: 1;
      width: 98px;
      height: 98px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      text-align: center;
      padding: 12px;
      color: var(--ink);
      background: white;
      border: 1px solid var(--line);
      box-shadow: 0 10px 28px rgba(60,64,67,.1);
      font-weight: 600;
      line-height: 1.15;
    }
    .orbit-dot {
      position: absolute;
      z-index: 2;
      width: 36px;
      height: 36px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      color: white;
      background: var(--green);
      box-shadow: 0 6px 18px rgba(13,111,91,.18);
      font-size: 12px;
      font-weight: 700;
    }
    .orbit-dot.go { top: 8px; left: 50%; transform: translateX(-50%); background: #b06000; }
    .orbit-dot.grow { top: 50%; right: 8px; transform: translateY(-50%); background: var(--blue); }
    .orbit-dot.govern { bottom: 8px; left: 50%; transform: translateX(-50%); background: var(--green); }
    .orbit-dot.do { top: 50%; left: 8px; transform: translateY(-50%); background: #8c5a00; }
    .flywheel-steps {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .flywheel-step {
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(255,255,255,.72);
      animation: pulseStep 8s ease-in-out infinite;
    }
    .flywheel-step:nth-child(2) { animation-delay: 1.6s; }
    .flywheel-step:nth-child(3) { animation-delay: 3.2s; }
    .flywheel-step:nth-child(4) { animation-delay: 4.8s; }
    .flywheel-step b { display: block; margin-bottom: 3px; font-size: 13px; font-weight: 650; }
    .flywheel-step span { color: var(--muted); font-size: 12px; }
    .cycle-note {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      padding: 9px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.66);
    }
    .cycle-note strong { color: var(--ink); font-weight: 650; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes pulseStep {
      0%, 100% { border-color: var(--line); background: rgba(255,255,255,.72); transform: translateY(0); }
      14%, 28% { border-color: rgba(176,96,0,.32); background: rgba(254,247,224,.78); transform: translateY(-1px); }
    }
    .marketplace-panel {
      margin-top: 10px;
      padding: 16px;
      border: 1px solid rgba(26,115,232,.18);
      border-radius: 10px;
      background: rgba(248,250,255,.78);
    }
    .brand-lockup { display: inline-flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
    .brand-mark {
      font-size: 30px;
      font-weight: 600;
      line-height: 1;
      letter-spacing: 0;
      color: var(--ink);
      text-shadow: none;
    }
    .brand-tag {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .welcome-main h2 { font-size: clamp(30px, 3.2vw, 46px); font-weight: 500; line-height: 1.08; margin-bottom: 12px; }
    .hero-copy { max-width: 720px; font-size: 15px; }
    .demo-callout {
      margin-top: 18px;
      padding: 14px;
      border: 1px solid #efd0b5;
      border-radius: 8px;
      background: rgba(255,248,241,.88);
    }
    .pipe-step, .stat, .item, .candidate, .score-row {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.92);
    }
    button.item {
      display: block;
      width: 100%;
      text-align: left;
      padding: 13px;
      font-weight: 400;
    }
    button.item h3 { color: var(--ink); }
    .create-panel { padding: 26px; }
    .sidebar { position: sticky; top: 18px; }
    .sidebar h2 {
      font-size: 20px;
      line-height: 1.18;
      overflow-wrap: anywhere;
    }
    .workflow-chip {
      margin-top: 14px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }
    .project-strip {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
      margin: 14px 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.72);
    }
    .project-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .project-list button { text-align: left; }
    .project-form {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(220px, 1fr) auto;
      gap: 8px;
      align-items: end;
      margin-top: 10px;
    }
    .step-number {
      width: 28px;
      height: 28px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: white;
      border: 1px solid var(--line);
      font-weight: 600;
    }
    .active .step-number { background: var(--green); color: white; border-color: var(--green); }
    .step b { font-weight: 600; }
    .content { min-height: 720px; }
    .review-shell {
      max-width: 1180px;
      margin: 24px auto;
    }
    .review-layout {
      display: grid;
      grid-template-columns: minmax(280px, .75fr) minmax(0, 1.25fr);
      gap: 16px;
      align-items: start;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 18px;
    }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .actions.compact { gap: 6px; }
    .actions.compact button { padding: 7px 10px; font-size: 13px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .grow-section {
      margin-top: 16px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(255,255,255,.76);
    }
    .grow-section:first-of-type { margin-top: 0; }
    .grow-kicker {
      color: var(--green);
      font-size: 12px;
      font-weight: 760;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    .source-picker {
      display: grid;
      gap: 8px;
      max-height: 360px;
      overflow: auto;
      padding-right: 4px;
    }
    .source-option {
      display: grid;
      grid-template-columns: 20px 1fr;
      gap: 8px;
      align-items: start;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
    }
    .source-option input { width: auto; margin-top: 3px; }
    .item { padding: 12px; }
    .item + .item { margin-top: 8px; }
    .item-title { font-weight: 600; overflow-wrap: anywhere; }
    .small { font-size: 13px; }
    .tiny { font-size: 12px; }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      letter-spacing: 0;
    }
    .hidden { display: none !important; }
    .empty {
      border: 1px dashed #bfd0cc;
      border-radius: 10px;
      padding: 22px;
      color: var(--muted);
      background: rgba(255,255,255,.52);
    }
    .status {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--green-soft);
      color: var(--green);
      font-weight: 600;
      font-size: 12px;
    }
    .status.amber { background: var(--amber-soft); color: #7a561f; }
    .status.blue { background: var(--blue-soft); color: var(--blue); }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 18px 0; }
    .stat { padding: 10px; }
    .stat b { display: block; font-size: 20px; font-weight: 600; }
    .method-box {
      border-left: 5px solid var(--green);
      padding: 16px;
      background: white;
      border-radius: 8px;
      border-top: 1px solid var(--line);
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }
    .candidate { padding: 0; overflow: hidden; }
    .candidate-header {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }
    .candidate-body { padding: 12px; white-space: pre-wrap; max-height: 320px; overflow: auto; }
    .scores { display: grid; gap: 8px; margin-top: 10px; }
    .score-row { padding: 8px 10px; display: grid; grid-template-columns: 150px 1fr 52px; gap: 10px; align-items: center; }
    .score-explain { margin-top: 10px; padding: 10px 12px; background: #f6faf8; border: 1px solid var(--line); border-radius: 6px; }
    .score-explain p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.35; }
    .score-explain ul { margin: 8px 0 0 18px; color: var(--muted); font-size: 12px; line-height: 1.35; }
    .bar { height: 9px; border-radius: 999px; background: #dfe8e5; overflow: hidden; }
    .bar > i { display: block; height: 100%; background: linear-gradient(90deg, var(--green), #c19048); }
    .quality-layout { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 14px; align-items: start; }
    .radar-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.84);
      padding: 12px;
    }
    .radar-svg { width: 100%; max-width: 240px; display: block; margin: 0 auto; }
    .radar-grid polygon, .radar-grid line { fill: none; stroke: #cbd8d5; stroke-width: 1; }
    .radar-shape { fill: rgba(8,118,95,.18); stroke: var(--green); stroke-width: 2; }
    .radar-labels text { fill: var(--muted); font-size: 9px; font-weight: 680; }
    .quality-score { text-align: center; margin-top: 8px; }
    .quality-score span { display: block; color: var(--muted); font-size: 12px; font-weight: 680; }
    .quality-score strong { display: block; font-size: 22px; line-height: 1.1; font-weight: 600; }
    .candidate.selected { border-color: rgba(8,118,95,.65); box-shadow: inset 0 0 0 1px rgba(8,118,95,.2); }
    .candidate.clickable { cursor: pointer; }
    .bucket-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; align-items: start; }
    .bucket { border: 1px solid var(--line); border-radius: 10px; background: rgba(255,255,255,.78); padding: 12px; min-height: 160px; }
    .bucket h3 { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .bucket .item { background: white; }
    .data-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0 10px; }
    .data-tabs button.active { background: var(--ink); color: white; border-color: var(--ink); }
    .results-table-wrap { border: 1px solid var(--line); border-radius: 10px; overflow: auto; background: rgba(255,255,255,.86); }
    table.results-table { width: 100%; border-collapse: collapse; min-width: 780px; }
    .results-table th, .results-table td { border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: middle; }
    .results-table th { color: var(--muted); font-size: 12px; font-weight: 650; background: rgba(244,248,247,.72); }
    .results-table tr:last-child td { border-bottom: 0; }
    .result-pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 5px 9px; font-size: 12px; font-weight: 650; background: var(--green-soft); color: var(--green); }
    .result-pill.reviewed { background: #e7f5ec; color: #17633a; }
    .result-pill.review { background: var(--amber-soft); color: #7a561f; }
    .result-pill.not_selected { background: var(--blue-soft); color: var(--blue); }
    .row-title { font-weight: 600; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .data-table-wrap { border: 1px solid var(--line); border-radius: 8px; overflow: auto; background: rgba(255,255,255,.84); }
    table.data-table { width: 100%; border-collapse: collapse; min-width: 760px; font-size: 12px; }
    .data-table th, .data-table td { border-bottom: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }
    .data-table th { color: var(--muted); font-weight: 720; background: var(--soft); }
    .data-table td { max-width: 360px; overflow-wrap: anywhere; }
    .pack-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .artifact-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 14px 0 18px; }
    .artifact-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.78);
      padding: 12px;
      min-height: 116px;
    }
    .artifact-card b { display: block; font-size: 20px; margin: 4px 0; }
    .workflow-graph {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.82);
      padding: 16px;
      overflow: auto;
    }
    .graph-row {
      min-width: 820px;
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 10px;
      align-items: stretch;
    }
    .graph-node {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 12px;
      position: relative;
    }
    .graph-node:not(:last-child)::after {
      content: "→";
      position: absolute;
      right: -18px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      font-weight: 700;
    }
    .graph-node strong { display: block; margin-bottom: 6px; }
    details.raw-memory { margin-top: 18px; }
    details.raw-memory summary { cursor: pointer; font-weight: 680; }
    pre {
      margin: 0;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      background: #10201d;
      color: #e5f4ef;
      border-radius: 8px;
      padding: 14px;
    }
    .toast {
      position: fixed;
      right: 24px;
      bottom: 24px;
      max-width: 420px;
      background: #10201d;
      color: white;
      padding: 12px 14px;
      border-radius: 8px;
      box-shadow: 0 16px 30px rgba(20,32,30,.25);
      z-index: 4;
    }
    .toast.error { background: #7a1f1f; }
    @media (max-width: 1100px) {
      .shell, .welcome, .review-layout { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .grid-3, .stats { grid-template-columns: 1fr 1fr; }
      .quality-layout { grid-template-columns: 1fr; }
      .flywheel-card { grid-template-columns: 1fr; }
      .flywheel-orbit { max-width: 280px; margin: 0 auto; width: 100%; }
    }
    @media (max-width: 720px) {
      header, main { padding-left: 16px; padding-right: 16px; }
      .grid-2, .pack-grid, .artifact-grid, .stats, .project-strip, .project-form, .flywheel-steps { grid-template-columns: 1fr; }
      .section-head { display: block; }
      .actions { margin-top: 12px; }
    }
  </style>
</head>
<body>
<header>
  <div>
    <h1 onclick="backHome()" title="Go home">PHEO</h1>
    <p class="muted">Continuous learning for reviewed AI work.</p>
  </div>
  <div class="status" id="header-status">Ready</div>
</header>

<main>
  <div id="welcome" class="welcome">
    <section class="card welcome-nav">
      <div class="nav-section">
        <button class="nav-link" onclick="document.getElementById('marketplace-section').scrollIntoView({behavior:'smooth'})">Marketplace <span>›</span></button>
      </div>
      <div class="nav-section">
        <div class="nav-section-title">Existing workflows</div>
        <div id="workflow-list" class="list"></div>
      </div>
    </section>

    <section class="card welcome-main">
      <div class="home-prompt">
      <div class="section-head" style="margin-bottom:12px">
        <div>
          <h2>Hi, I’m your governance apprentice.</h2>
          <p class="muted hero-copy">Tell me where to start. I’ll learn your workflow, govern AI outputs, and turn human judgment into memory for the next run.</p>
          <div class="flywheel-card" aria-label="PHEO continuous learning flywheel">
            <div class="flywheel-orbit">
              <div class="orbit-line"></div>
              <div class="orbit-core">Continuous<br>learning</div>
              <div class="orbit-dot go">Go</div>
              <div class="orbit-dot grow">Grow</div>
              <div class="orbit-dot govern">Gov</div>
              <div class="orbit-dot do">Do</div>
            </div>
            <div class="flywheel-steps">
              <div class="flywheel-step"><b>PHEO Go</b><span>Ingest source material, criteria, and examples. I reshape them to infer your method.</span></div>
              <div class="flywheel-step"><b>PHEO Grow</b><span>Observe outputs from your agent, endpoint, or workflow. I branch, score, and route the work.</span></div>
              <div class="flywheel-step"><b>PHEO Govern</b><span>Humans approve, edit, reject, or escalate. Every judgment becomes decision memory with a receipt.</span></div>
              <div class="flywheel-step"><b>PHEO Do</b><span>Run the next action with the learned workflow instead of rediscovering it each time.</span></div>
              <div class="cycle-note"><strong>Cycle 2:</strong> the next similar case starts with the best known path.</div>
            </div>
          </div>
        </div>
        <div class="actions">
          <button class="primary nowrap" onclick="toggleCreateForm(true)">+ New workflow</button>
        </div>
      </div>
      </div>
      <div id="create-form" class="hidden">
        <label>Workflow name</label>
        <input id="workflow-name" placeholder="medical_review">
        <label>Task</label>
        <textarea id="workflow-objective" placeholder="Example: Review AI-selected scientific papers before they are trusted for downstream analysis."></textarea>
        <label>Output source</label>
        <select id="workflow-mode">
          <option value="api_endpoint">OpenAI-compatible API endpoint</option>
          <option value="manual_review" disabled>Paste outputs manually (available inside Grow)</option>
          <option value="trace_import" disabled>LangChain / trace import (coming soon in guided setup)</option>
          <option value="business_connector" disabled>Business connector (coming soon)</option>
        </select>
        <label>Endpoint URL</label>
        <input id="workflow-endpoint" placeholder="https://api.openai.com/v1 or https://openrouter.ai/api/v1">
        <label>API key</label>
        <input id="workflow-api-key" type="password" placeholder="sk-...">
        <label>Model</label>
        <input id="workflow-model" placeholder="gpt-4o-mini or openai/gpt-4o-mini">
        <div class="actions" style="margin-top:14px">
          <button class="primary" onclick="createWorkflow()">Create and continue</button>
          <button onclick="toggleCreateForm(false)">Cancel</button>
        </div>
      </div>
      <div id="marketplace-section" class="marketplace-panel">
      <h3>Marketplace</h3>
      <p class="muted small" style="margin-bottom:12px">Start from a workflow template, then keep its data and decisions isolated.</p>
      <div class="grid-2">
        <button class="item clickable" onclick="startMedicalTemplate()">
          <h3>Medical review</h3>
          <p class="muted small">Start with 10 real PMC OA breast-cancer papers.</p>
        </button>
        <button class="item clickable" onclick="startFinanceDemo()">
          <h3>Finance receipt review</h3>
          <p class="muted small">Open the sample receipt-review apprentice with demo policy material.</p>
        </button>
      </div>
      </div>
    </section>
  </div>

  <div id="review-page" class="review-shell hidden">
    <section class="card pad">
      <div class="section-head">
        <div>
          <h2 id="review-title">Review case</h2>
          <p id="review-subtitle" class="muted"></p>
        </div>
        <span id="review-status" class="status amber">Pending review</span>
      </div>
      <div class="review-layout">
        <div>
          <div class="item">
            <h3>Observed output</h3>
            <p id="review-observed" class="small" style="white-space:pre-wrap"></p>
          </div>
          <div class="item">
            <h3>Review decision</h3>
            <label>Selected output</label>
            <select id="review-selected"></select>
            <label>Action</label>
            <select id="review-action">
              <option value="approve">Approve</option>
              <option value="edit">Edit</option>
              <option value="reject">Reject</option>
              <option value="escalate">Escalate</option>
            </select>
            <label>Reason</label>
            <textarea id="review-reason" placeholder="Explain why this output should be trusted, changed, rejected, or escalated.">Most grounded and reviewable.</textarea>
            <label>Edited output, if needed</label>
            <textarea id="review-correction" placeholder="Optional corrected output. Leave blank for approval."></textarea>
            <div class="actions" style="margin-top:12px">
              <button class="primary" onclick="capturePacketReview()">Capture review</button>
              <button onclick="backToPheoFromReview()">Back to PHEO</button>
            </div>
            <p id="review-captured-note" class="muted small hidden" style="margin-top:10px">
              Review saved. If this page was opened by a one-shot demo, return to the terminal;
              the temporary browser server may close after the export finishes. For a persistent
              UI, run the printed <span class="mono">pheo start</span> command.
            </p>
          </div>
        </div>
        <div>
          <div id="review-quality-panel" style="margin-bottom:14px"></div>
          <div id="review-candidates" class="grid-3"></div>
        </div>
      </div>
    </section>
  </div>

  <div id="app" class="shell hidden">
    <aside class="card sidebar pad">
      <h2 id="side-name">Workflow</h2>
      <p id="side-objective" class="muted small"></p>
      <div class="workflow-chip">
        <div class="tiny muted">Active review path</div>
        <div class="item-title" id="side-domain"></div>
      </div>
      <h3 style="margin-top:18px">Flow</h3>
      <div class="list">
        <button id="step-go" class="step" onclick="go('go')"><span class="step-number">1</span><span><b>PHEO Go</b><br><span class="muted small">Onboarding and sources.</span></span></button>
        <button id="step-grow" class="step" onclick="go('grow')"><span class="step-number">2</span><span><b>PHEO Grow</b><br><span class="muted small">Review work from any system.</span></span></button>
        <button id="step-decisions" class="step" onclick="go('decisions')"><span class="step-number">3</span><span><b>Decisions</b><br><span class="muted small">Receipts, memory, and exports.</span></span></button>
      </div>
      <div class="stats">
        <div class="stat"><span class="muted tiny">Sources</span><b id="count-corpus">0</b></div>
        <div class="stat"><span class="muted tiny">Reviews</span><b id="count-runs">0</b></div>
        <div class="stat"><span class="muted tiny">Decisions</span><b id="count-decisions">0</b></div>
        <div class="stat"><span class="muted tiny">Pairs</span><b id="count-pairs">0</b></div>
      </div>
    </aside>

    <section class="card content pad">
      <div id="panel-go" class="panel">
        <div class="section-head">
          <div>
            <h2>PHEO Go</h2>
            <p class="muted">Give me the material and rules for this workflow. I will build the review method from only this workflow’s sources.</p>
          </div>
          <button class="primary" onclick="go('grow')" id="go-ready-button">Go to Grow</button>
        </div>
        <div id="go-onboard-status" class="empty" style="margin-bottom:14px">Connect sources and rules, then onboard the apprentice.</div>
        <div class="grid-2">
          <div>
            <input id="corpus-title" class="hidden" value="Workflow source material">
            <label>Corpus / source material</label>
            <textarea id="corpus-text" oninput="renderOnboardStatus()" placeholder="Paste documents, examples, tickets, papers, receipts, policies, or notes this workflow should learn from."></textarea>
            <label>Rules / criteria</label>
            <textarea id="rules-text" oninput="renderOnboardStatus()" placeholder="Paste the criteria, operating rules, policy notes, or review instructions reviewers should use."></textarea>
            <label>Add files</label>
            <input id="source-files" type="file" multiple onchange="loadSourceFiles()">
            <div class="actions" style="margin-top:12px">
              <button id="onboard-button" class="primary" onclick="onboardApprentice(this)">Onboard apprentice</button>
            </div>
          </div>
          <div>
            <h3>Connected sources</h3>
            <div id="corpus-list" class="list empty">No data yet. Add source material or choose a template.</div>
            <p class="muted small" style="margin-top:12px">Each workflow has separate source material, rules, outputs, decisions, and memory.</p>
          </div>
        </div>
      </div>

      <div id="panel-grow" class="panel hidden">
        <div class="section-head">
          <div>
            <h2>PHEO Grow</h2>
            <p class="muted">Observe work from your system, score it against the onboarded method, and send uncertain items to human judgment.</p>
          </div>
          <div class="status amber">Human gate</div>
        </div>
        <div class="grow-section">
          <div class="grow-kicker">1. Observe</div>
          <div class="grid-2">
            <div>
              <h3>Connected sources</h3>
              <p class="muted small" style="margin-bottom:10px">Choose the data from PHEO Go that this run should observe.</p>
              <div id="grow-source-picker" class="source-picker empty">No connected source data yet.</div>
              <div class="actions compact" style="margin-top:10px">
                <button onclick="selectAllGrowSources()">Select all</button>
                <button onclick="clearGrowSourceSelection()">Clear selection</button>
              </div>
            </div>
            <div>
              <label>Task</label>
              <textarea id="task-goal" placeholder="What should this workflow decide or review?"></textarea>
              <label>Object data</label>
              <textarea id="customer-object" placeholder="Paste the paper, receipt, ticket, case, file excerpt, or business object."></textarea>
              <details class="item" style="margin-top:12px">
                <summary><b>Agentic endpoint</b></summary>
                <div style="margin-top:10px">
                  <p class="muted small">Use this when your current AI system returns the output.</p>
                  <label>Endpoint base URL</label>
                  <input id="endpoint-url" placeholder="https://openrouter.ai/api/v1">
                  <label>API key</label>
                  <input id="endpoint-key" type="password" placeholder="sk-...">
                  <label>Model</label>
                  <input id="endpoint-model" placeholder="openrouter/auto">
                  <div class="actions" style="margin-top:12px">
                    <button class="primary" onclick="callEndpoint()">Run endpoint</button>
                  </div>
                </div>
              </details>
              <details class="item" style="margin-top:12px">
                <summary><b>Paste outputs manually</b></summary>
                <div style="margin-top:10px">
                  <div class="grid-3">
                    <div><label>Output 1</label><textarea id="candidate-1" placeholder="Paste output from your workflow, agent, API, or batch job."></textarea></div>
                    <div><label>Output 2</label><textarea id="candidate-2" placeholder="Paste another candidate if available."></textarea></div>
                    <div><label>Output 3</label><textarea id="candidate-3" placeholder="Paste a third output if available."></textarea></div>
                  </div>
                  <input id="generator-label" class="hidden" value="workflow_output">
                  <div class="actions" style="margin-top:14px">
                    <button class="primary" onclick="createRun()">Score outputs</button>
                    <button onclick="fillDemoReceiptOutputs()">Use demo receipt outputs</button>
                  </div>
                </div>
              </details>
              <details class="item" style="margin-top:12px">
                <summary><b>Import traces</b></summary>
                <div style="margin-top:10px">
                  <p class="muted small">Paste a trace export when the workflow already records model or tool output.</p>
                  <div class="grid-2" style="margin-top:10px">
                    <div>
                      <label>Trace source</label>
                      <select id="trace-source">
                        <option value="langsmith">LangChain / LangSmith</option>
                        <option value="weave">W&B Weave</option>
                        <option value="noveum">Noveum Trace</option>
                        <option value="opentelemetry">OpenTelemetry spans</option>
                      </select>
                    </div>
                    <div>
                      <label>Trace task</label>
                      <input id="trace-goal" placeholder="Invoice review, paper screening, support reply review">
                    </div>
                  </div>
                  <label>Trace JSON</label>
                  <textarea id="trace-payload" placeholder='{"inputs":{"prompt":"Review invoice exception"},"outputs":{"output":"Approve only after policy check."}}'></textarea>
                  <div class="actions" style="margin-top:12px">
                    <button class="blue" onclick="importTraces()">Import traces</button>
                  </div>
                </div>
              </details>
            </div>
          </div>
          <div id="starter-review-panel" style="margin-top:16px"></div>
        </div>
        <div class="grow-section">
          <div class="grow-kicker">2. Results</div>
          <div id="run-results"></div>
        </div>
      </div>

      <div id="panel-decisions" class="panel hidden">
        <div class="section-head">
          <div>
            <h2>Decisions</h2>
            <p class="muted">This is what your reviews create: source provenance, approved rules, scored outputs, decisions, examples, receipts, memory, and an audit trail. These judgments improve the next similar review.</p>
          </div>
          <div class="actions compact">
            <button class="blue" onclick="loadPack()">Refresh</button>
            <button class="primary" onclick="downloadPack()">Full JSON</button>
            <button onclick="downloadJsonl('preferences')">Preferences</button>
            <button onclick="downloadJsonl('examples')">Examples</button>
            <button onclick="downloadJsonl('checks')">Checks</button>
          </div>
        </div>
        <div id="pack-summary" class="pack-grid"></div>
        <div id="artifact-explain" class="artifact-grid"></div>
        <div id="data-viewer"></div>
        <details class="raw-memory">
          <summary>Full memory JSON preview</summary>
          <pre id="pack-output" style="margin-top:10px">{}</pre>
        </details>
      </div>
    </section>
  </div>
</main>

<div id="toast" class="toast hidden"></div>

<script>
let workflow = null;
let store = null;
let currentRun = null;
let reviewPacket = null;
let activeStep = 'go';
let activeDataTable = 'graph';
let autoOpenStore = '';
let projectState = null;
let workflowEndpointDraft = {};
let selectedGrowSourceIds = new Set();
let growSourceSelectionTouched = false;
const SESSION_WORKFLOW_KEY = 'pheo.activeWorkflowId';
const REVIEW_CHANNEL = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('pheo-review') : null;

const DEMO_FINANCE_RECEIPT_POLICY = `Finance receipt review policy.

The AI may draft a short finance receipt exception note, but a person must
approve, edit, reject, or escalate before the note is used for payment,
reconciliation, or audit follow-up.

Must check:
- Escalate when approval status is unclear or no approver is identified.
- Escalate when receipt, purchase order, or vendor support is missing.
- Flag possible duplicate receipts before saying the item is clear.
- Keep the final note factual and tied to the receipt context.

Must not do:
- Do not say a receipt can proceed when approval or support is unclear.
- Do not invent approvers, purchase-order matches, or payment clearance.`;

const DEMO_FINANCE_OBJECTIVE = `Review finance receipt exception notes before payment-related action is released.
Use this for the Hello World demo: source material becomes rules, rules govern review, and each human judgment becomes local memory.`;

const DEMO_RECEIPT_OUTPUTS = [
  `Receipt FIN-1007 can proceed after review.

Vendor: Northstar Office Supplies
Amount: $18,420.00
Approval status: unclear. No approver identified.
Support: purchase-order match missing.`,
  `Receipt FIN-1007 should be held.

The approval owner is not identified and purchase-order support is missing. Ask finance operations to confirm the approver and attach support before any payment-related action.`,
  `Escalate receipt FIN-1007.

Reason: approval status is unclear and purchase-order support is missing. Do not say the receipt can proceed until a reviewer confirms the support package.`
];

const MEDICAL_REVIEW_RULES = `Review question:
Which breast-cancer papers should be included for downstream scientific evidence review?

Must check:
- C1 Disease fit: the paper is specifically about breast cancer or a directly relevant breast-cancer subgroup.
- C2 Scientific relevance: the paper has clinical, translational, epidemiological, real-world, biomarker, safety, or outcomes relevance.
- C3 Extractable evidence: the paper contains evidence that can be extracted for the review question, not only background commentary.
- C4 Review context: the paper states enough population, intervention or exposure, comparator, endpoint, outcome, or study-design context to support a decision.
- C5 Synthesis utility: the paper is useful for downstream evidence synthesis, not generic background only.

Must not do:
- Do not include papers that only mention breast cancer tangentially.
- Do not include papers with no extractable evidence for the review question.
- Do not hide uncertainty; send borderline papers to human review.`;

const MEDICAL_PAPER_CASES = [
  {
    id: 'P001',
    title: 'Breast cancer-related lymphedema and recurrence of breast cancer: Protocol for a prospective cohort study in China',
    pmcid: 'PMC10187897',
    target: 'selected',
    excerpt: 'Introduction The primary aim is to determine factors associated with breast cancer-related lymphedema and to identify associated factors for recurrence of breast cancer and depression. A cohort study of females with unilateral breast cancer will be conducted in West China Hospital. Population, outcomes, recurrence, and extractable cohort variables are described.'
  },
  {
    id: 'P002',
    title: 'Clinical significance of HER2-low expression in early breast cancer: a nationwide study from the Korean Breast Cancer Society',
    pmcid: 'PMC8935777',
    target: 'selected',
    excerpt: 'Background There is increasing interest in HER2-low breast cancer with promising data from clinical trials using novel anti-HER2 antibody-drug conjugates. This nationwide breast cancer study compares clinicopathological characteristics and survival outcomes, with extractable endpoints and subgroup context.'
  },
  {
    id: 'P003',
    title: 'Up-regulation of bone marrow stromal protein 2 (BST2) in breast cancer with bone metastasis',
    pmcid: 'PMC2674058',
    target: 'review',
    excerpt: 'Background Bone metastases are frequent complications of breast cancer. The study investigates BST2 expression and its role in bone metastatic breast cancer using cell lines and tissue arrays. Breast cancer disease fit is strong, but review context and downstream synthesis utility may need human confirmation.'
  },
  {
    id: 'P004',
    title: 'Assessment of outcomes and novel immune biomarkers in metaplastic breast cancer',
    pmcid: 'PMC6961248',
    target: 'selected',
    excerpt: 'Background Metaplastic breast cancer remains poorly characterized given its rarity and heterogeneity. This retrospective cohort evaluates outcomes and immune biomarkers, including population context, endpoints, and extractable evidence for synthesis.'
  },
  {
    id: 'P005',
    title: 'Comprehensive profiles and diagnostic value of menopausal-specific gut microbiota in premenopausal breast cancer',
    pmcid: 'PMC8569190',
    target: 'review',
    excerpt: 'The study investigates gut microbiota profiles in premenopausal breast cancer and evaluates menopausal-specific microbial signatures and diagnostic value. Breast cancer relevance is present, but the reviewer should confirm whether the evidence is useful for the downstream clinical synthesis.'
  },
  {
    id: 'P006',
    title: 'Comparing multifocal with unifocal breast cancer and the relationship with survival: national cohort study',
    pmcid: 'PMC13150851',
    target: 'selected',
    excerpt: 'Background The prognostic relevance of multifocal and multicentric breast cancer remains unclear. This national cohort study explores survival differences between multifocal and unifocal breast cancer, with population, comparator, outcomes, and extractable survival evidence.'
  },
  {
    id: 'P007',
    title: 'Pre-diagnosis alcohol consumption and mortality risk among black women and white women with invasive breast cancer',
    pmcid: 'PMC6693233',
    target: 'review',
    excerpt: 'Background Alcohol consumption is associated with increased breast cancer risk, but association with subsequent breast cancer death is unclear. The study follows women with invasive breast cancer. It has relevant outcomes, but exposure framing may be borderline for the current review question.'
  },
  {
    id: 'P008',
    title: 'Serum Trace Elements and Their Associations with Breast Cancer Subgroups in Korean Breast Cancer Patients',
    pmcid: 'PMC6357144',
    target: 'not_selected',
    excerpt: 'The study investigates serum trace elements in breast cancer patients compared to controls. It is biomarker-adjacent, but the available excerpt is thin on population, intervention or exposure context, endpoint definition, and extractable downstream synthesis variables.'
  },
  {
    id: 'P009',
    title: 'Association of Family History with the Development of Breast Cancer: A Cohort Study of 129,374 Women in KoGES Data',
    pmcid: 'PMC8296242',
    target: 'not_selected',
    excerpt: 'Background Breast cancer is mentioned as a common cancer among women. This cohort uses KoGES data to examine family history and development risk. For this review, the excerpt lacks treatment, intervention, outcome, or synthesis-ready clinical evidence beyond broad risk association.'
  },
  {
    id: 'P010',
    title: 'Circulating High-Molecular-Weight Adiponectin Level Is Related with Breast Cancer Risk Better than Total Adiponectin',
    pmcid: 'PMC4466435',
    target: 'not_selected',
    excerpt: 'The study examines adiponectin forms associated with breast cancer risk. It is risk-marker oriented and the excerpt does not provide enough review context, intervention or comparator framing, or extractable downstream evidence for the selected synthesis question.'
  }
];

const FINANCE_REVIEW_RULES = `Review question:
Which finance receipt or invoice exception notes can be trusted before payment-related action?

Must check:
- Approval clarity: a named approver or approval path is present.
- Support package: receipt, invoice, purchase order, or vendor support is present.
- Duplicate risk: possible duplicate receipts are flagged before clearance.
- Exception handling: unclear or high-risk cases are escalated.
- Factual note: the final note stays tied to the provided receipt context.

Must not do:
- Do not say a receipt can proceed when approval or support is unclear.
- Do not invent approvers, purchase-order matches, or payment clearance.
- Do not hide uncertainty; escalate when the support package is incomplete.`;

const FINANCE_RECEIPT_CASES = [
  {
    id: 'FIN-1007',
    title: 'Northstar Office Supplies receipt',
    excerpt: 'Vendor: Northstar Office Supplies. Amount: $18,420. Approval status unclear. No approver identified. Purchase-order match missing.'
  },
  {
    id: 'FIN-1019',
    title: 'Bayline Events catering receipt',
    excerpt: 'Vendor: Bayline Events. Amount: $6,220. Approval from events lead attached. Receipt attached. Possible duplicate expense submitted two days earlier.'
  },
  {
    id: 'FIN-1033',
    title: 'Aster Labs equipment invoice',
    excerpt: 'Vendor: Aster Labs. Amount: $31,480. Purchase order attached. Department approval attached. Vendor tax form missing.'
  },
  {
    id: 'FIN-1044',
    title: 'Orion Cloud Services overage invoice',
    excerpt: 'Vendor: Orion Cloud Services. Amount: $48,800. Usage report attached. IT director approval attached. Finance budget owner note missing.'
  },
  {
    id: 'FIN-1058',
    title: 'Meridian Travel receipt bundle',
    excerpt: 'Vendor: Meridian Travel. Amount: $9,760. Multiple receipts attached. Approval path unclear for one traveler. Two line items lack matching itinerary support.'
  }
];

document.addEventListener('DOMContentLoaded', () => {
  if (REVIEW_CHANNEL) {
    REVIEW_CHANNEL.onmessage = (event) => {
      const payload = event.data || {};
      if (payload.type === 'review-captured' && workflow && payload.workflowId === workflow.id) {
        hydrateWorkflow().catch(showError);
      }
    };
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && workflow && activeStep === 'grow') {
      hydrateWorkflow().catch(showError);
    }
  });
  const reviewMatch = window.location.pathname.match(/^\\/review\\/([^/]+)$/);
  if (reviewMatch) {
    loadReviewPacket(reviewMatch[1]).catch(showError);
  } else {
    autoOpenStore = new URLSearchParams(window.location.search).get('store') || rememberedWorkflowId();
    loadProjects().then(loadWorkflows).catch(showError);
  }
});

function rememberedWorkflowId() {
  try {
    return sessionStorage.getItem(SESSION_WORKFLOW_KEY) || '';
  } catch (_) {
    return '';
  }
}

function rememberWorkflow(id) {
  if (!id) return;
  try {
    sessionStorage.setItem(SESSION_WORKFLOW_KEY, id);
  } catch (_) {}
}

function clearRememberedWorkflow() {
  try {
    sessionStorage.removeItem(SESSION_WORKFLOW_KEY);
  } catch (_) {}
}

async function findWorkflowBySkill(skill) {
  const data = await api('/v1/workflows');
  return (data.workflows || []).find(item => item.skill === skill || item.name === skill) || null;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {'Content-Type': 'application/json', ...(options.headers || {})}
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(data.message || data.error || response.statusText);
  return data;
}

async function loadWorkflows() {
  const data = await api('/v1/workflows');
  const target = document.getElementById('workflow-list');
  if (!data.workflows || !data.workflows.length) {
    target.innerHTML = '<div class="muted small">No workflows yet.</div>';
    return;
  }
  target.innerHTML = data.workflows.map(item => `
    <button class="nav-link" onclick="selectWorkflow('${escapeAttr(item.id)}')">
      <span><b>${escapeHtml(item.name)}</b><br><span class="muted small">${escapeHtml(item.domain || 'workflow')}</span></span>
      <span>↗</span>
    </button>
  `).join('');
  if (autoOpenStore) {
    const ref = autoOpenStore;
    autoOpenStore = '';
    await selectWorkflow(ref);
  }
}

async function loadProjects() {
  projectState = await api('/v1/projects');
  renderProjects();
}

function renderProjects() {
  const current = projectState && projectState.current_project || {};
  const projects = projectState && projectState.projects || [];
  const currentNode = document.getElementById('project-current');
  const countNode = document.getElementById('project-count');
  const listNode = document.getElementById('project-list');
  if (!currentNode || !countNode || !listNode) return;
  currentNode.innerHTML = `
    <b>${escapeHtml(current.name || 'local project')}</b>
    <br><span class="mono tiny">${escapeHtml(current.path || '')}</span>
    <br><span class="muted tiny">Database: ${escapeHtml(current.database || '')}</span>
  `;
  countNode.textContent = `${projects.length} project${projects.length === 1 ? '' : 's'}`;
  if (!projects.length) {
    listNode.innerHTML = '<div class="empty">No registered projects yet. The current server project is available.</div>';
    return;
  }
  listNode.innerHTML = projects.map(item => `
    <button class="step ${item.current ? 'active' : ''}" onclick="switchProject('${escapeAttr(item.name)}')">
      <span class="step-number">${item.current ? '✓' : '↗'}</span>
      <span><b>${escapeHtml(item.name)}</b><br><span class="muted small">${escapeHtml(item.path)}</span></span>
    </button>
  `).join('');
}

async function createProject() {
  const name = value('project-name');
  if (!name) throw new Error('Name the project first.');
  projectState = await api('/v1/projects', {method: 'POST', body: JSON.stringify({
    name,
    path: value('project-path'),
    activate: true,
    make_current: true
  })});
  workflow = null;
  store = null;
  renderProjects();
  await loadWorkflows();
  toast('Project created. Create a workflow inside it.');
}

async function switchProject(ref) {
  projectState = await api('/v1/projects/current', {method: 'POST', body: JSON.stringify({ref})});
  workflow = null;
  store = null;
  currentRun = null;
  reviewPacket = null;
  document.getElementById('app').classList.add('hidden');
  document.getElementById('review-page').classList.add('hidden');
  document.getElementById('welcome').classList.remove('hidden');
  renderProjects();
  await loadWorkflows();
  toast('Project switched. Workflows below belong to the selected project.');
}

function toggleCreateForm(force) {
  const form = document.getElementById('create-form');
  const shouldOpen = force === undefined ? form.classList.contains('hidden') : force;
  form.classList.toggle('hidden', !shouldOpen);
  if (shouldOpen) document.getElementById('workflow-name').focus();
}

async function createWorkflow() {
  const name = value('workflow-name');
  if (!name) throw new Error('Name the workflow first.');
  const goal = value('workflow-objective');
  if (!goal) throw new Error('Describe the task before creating the workflow.');
  workflowEndpointDraft = {
    task: goal,
    endpointUrl: value('workflow-endpoint'),
    apiKey: value('workflow-api-key'),
    model: value('workflow-model'),
    mode: value('workflow-mode') || 'api_endpoint'
  };
  const data = await api('/v1/workflows', {method: 'POST', body: JSON.stringify({
    name,
    domain: 'workflow',
    objective: goal,
    skill: name,
    force_new: true
  })});
  workflow = data.workflow;
  resetGrowSourceSelection();
  await hydrateWorkflow();
  showApp();
  applyWorkflowDraft();
  go(nextStep());
  toast('Workflow created. Continue where you left off.');
}

async function startMedicalTemplate() {
  const existing = await findWorkflowBySkill('medical_review');
  if (existing) {
    await selectWorkflow(existing.id);
    toast('Medical review workflow opened where you left off.');
    return;
  }
  const created = await api('/v1/workflows', {method: 'POST', body: JSON.stringify({
    name: 'medical_review',
    domain: 'life_sciences',
    objective: 'Review scientific evidence against approved criteria before downstream use.',
    skill: 'medical_review',
    force_new: true
  })});
  workflowEndpointDraft = {
    task: 'Review scientific evidence against approved criteria before downstream use.',
    endpointUrl: '',
    apiKey: '',
    model: '',
    mode: 'api_endpoint'
  };
  workflow = (await api(`/v1/workflows/${created.workflow.id}`)).workflow;
  resetGrowSourceSelection();
  await hydrateWorkflow();
  showApp();
  applyWorkflowDraft();
  await attachStarterSources('medical');
  go(nextStep());
  toast('Medical review starter corpus attached.');
}

async function startFinanceDemo() {
  const existing = await findWorkflowBySkill('finance_receipt_review');
  if (existing) {
    await selectWorkflow(existing.id);
    toast('Finance workflow opened where you left off.');
    return;
  }
  const created = await api('/v1/workflows', {method: 'POST', body: JSON.stringify({
    name: 'finance_receipt_review',
    domain: 'finance',
    objective: DEMO_FINANCE_OBJECTIVE,
    skill: 'finance_receipt_review',
    force_new: true
  })});
  const demo = created.workflow;
  workflow = (await api(`/v1/workflows/${demo.id}`)).workflow;
  resetGrowSourceSelection();
  workflowEndpointDraft = {
    task: 'Review this finance receipt note before any payment-related action.',
    endpointUrl: '',
    apiKey: '',
    model: '',
    mode: 'manual_review'
  };
  await hydrateWorkflow();
  showApp();
  applyWorkflowDraft();
  await attachStarterSources('finance');
  go(nextStep());
  toast('Finance receipt starter set attached.');
}

async function selectWorkflow(id) {
  workflow = (await api(`/v1/workflows/${id}`)).workflow;
  rememberWorkflow(workflow.id);
  workflowEndpointDraft = {};
  resetGrowSourceSelection();
  await hydrateWorkflow();
  showApp();
  go(nextStep());
}

async function hydrateWorkflow() {
  store = await api(`/v1/workflows/${workflow.id}/preference-store`);
  pruneSelectedGrowSources();
  renderShell();
  renderCorpus();
  renderMethodology();
  renderRuns();
  await renderPack(false);
}

function showApp() {
  document.getElementById('welcome').classList.add('hidden');
  document.getElementById('review-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
}

function applyWorkflowDraft() {
  if (!workflowEndpointDraft) return;
  setIfPresent('task-goal', workflowEndpointDraft.task || (workflow && workflow.objective) || '');
  setIfPresent('endpoint-url', workflowEndpointDraft.endpointUrl || '');
  setIfPresent('endpoint-key', workflowEndpointDraft.apiKey || '');
  setIfPresent('endpoint-model', workflowEndpointDraft.model || '');
}

function backHome() {
  workflow = null;
  store = null;
  clearRememberedWorkflow();
  resetGrowSourceSelection();
  document.getElementById('app').classList.add('hidden');
  document.getElementById('review-page').classList.add('hidden');
  document.getElementById('welcome').classList.remove('hidden');
  loadProjects().then(loadWorkflows).catch(showError);
}

function resetGrowSourceSelection() {
  selectedGrowSourceIds = new Set();
  growSourceSelectionTouched = false;
}

function backToPheoFromReview() {
  const id = workflow && workflow.id;
  window.location.href = id ? `/?store=${encodeURIComponent(id)}` : '/';
}

async function loadReviewPacket(packetId) {
  reviewPacket = await api(`/v1/review-packets/${encodeURIComponent(packetId)}`);
  workflow = reviewPacket.workflow;
  document.getElementById('welcome').classList.add('hidden');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('review-page').classList.remove('hidden');
  renderReviewPage();
}

function renderReviewPage() {
  const packet = reviewPacket.packet || {};
  const point = reviewPacket.review_point || {};
  const observation = reviewPacket.observation || {};
  const run = reviewPacket.run || {};
  const candidates = reviewPacket.candidates || [];
  const recommended = reviewPacket.recommended || candidates[0] || {};
  const reviewBucket = bucketForReviewPacket(packet, recommended, run);
  document.getElementById('review-title').textContent = reviewItemTitle({packet, run, recommended, bucket: reviewBucket});
  document.getElementById('review-subtitle').textContent = workflow
    ? `${workflow.name} · ${workflow.domain || 'local workflow'}`
    : 'Local PHEO review';
  const status = document.getElementById('review-status');
  status.textContent = packet.status === 'reviewed' ? 'Judgment saved' : resultLabel(reviewBucket);
  status.className = `status ${packet.status === 'reviewed' ? '' : reviewBucket === 'review' ? 'amber' : reviewBucket === 'not_selected' ? 'blue' : ''}`;
  document.getElementById('review-observed').textContent = observation.output || '';
  document.getElementById('review-selected').innerHTML = candidates.map(item => (
    `<option value="${item.index}">Output ${item.index + 1}${item.recommended ? ' · recommended' : ''}</option>`
  )).join('');
  document.getElementById('review-selected').value = String(recommended.index ?? 0);
  document.getElementById('review-selected').onchange = () => renderQualityPanel('review-quality-panel', candidates, Number(value('review-selected')));
  renderQualityPanel('review-quality-panel', candidates, recommended.index ?? 0);
  document.getElementById('review-candidates').innerHTML = candidates.map(candidate => renderReviewCandidate(candidate, 'review-selected', 'review-quality-panel')).join('');
}

function renderReviewCandidate(candidate, selectId = '', qualityPanelId = '') {
  const scores = candidate.scores || {};
  const mean = pct(scores.mean_score);
  const click = selectId ? `onclick="selectCandidate(${candidate.index}, '${selectId}', '${qualityPanelId}')"` : '';
  return `
    <div class="candidate clickable" data-candidate-index="${candidate.index}" ${click}>
      <div class="candidate-header">
        <strong>Output ${candidate.index + 1}</strong>
        <span class="status ${candidate.recommended ? '' : 'amber'}">${candidate.recommended ? 'Recommended' : 'Rank ' + (candidate.rank || '-')} · ${mean}</span>
      </div>
      <div class="candidate-body">${escapeHtml(candidate.output)}</div>
      <div class="pad">
        <div class="scores">
          ${scoreRow('Rules fit', scores.methodology_fit)}
          ${scoreRow('Grounding', scores.grounding)}
          ${scoreRow('Action', scores.actionability)}
          ${scoreRow('Context', scores.context_sensitivity)}
          ${scoreRow('Safety', scores.safety)}
          ${scoreRow('Clarity', scores.clarity)}
        </div>
        ${scoreExplanation(scores)}
      </div>
    </div>
  `;
}

async function capturePacketReview() {
  if (!reviewPacket || !reviewPacket.packet) throw new Error('No review case loaded.');
  const result = await api(`/v1/review-packets/${reviewPacket.packet.id}/reviews`, {method: 'POST', body: JSON.stringify({
    selected_index: Number(value('review-selected')),
    action: value('review-action') || 'approve',
    reason: value('review-reason') || 'Reviewed by human.',
    corrected_output: value('review-correction'),
  })});
  toast('Review captured. Decisions and memory were written.');
  const note = document.getElementById('review-captured-note');
  if (note) note.classList.remove('hidden');
  await loadReviewPacket(result.packet.id);
  const workflowId = workflow && workflow.id;
  if (workflowId) {
    notifyReviewCaptured(workflowId, result.packet.id);
    await hydrateWorkflow();
  }
}

function notifyReviewCaptured(workflowId, packetId) {
  if (!REVIEW_CHANNEL) return;
  REVIEW_CHANNEL.postMessage({type: 'review-captured', workflowId, packetId});
}

function renderShell() {
  document.getElementById('side-name').textContent = workflow.name;
  document.getElementById('side-objective').textContent = workflow.objective || 'Review and remember a repeated business workflow.';
  document.getElementById('side-domain').textContent = workflow.domain || 'general';
  const corpus = store.corpus || [];
  const runs = store.review_packets || store.runs || [];
  const decisions = store.decisions || [];
  const pairs = store.preference_pairs || [];
  const humanDecisions = humanItems(decisions);
  const humanPairs = humanItems(pairs);
  document.getElementById('count-corpus').textContent = reviewableCorpus().length;
  document.getElementById('count-runs').textContent = runs.length;
  document.getElementById('count-decisions').textContent = humanDecisions.length;
  document.getElementById('count-pairs').textContent = humanPairs.length;
  document.getElementById('header-status').textContent = humanDecisions.length ? 'Learning' : 'Ready';
  const ready = document.getElementById('go-ready-button');
  if (ready) {
    const canGrow = activeCorpus().length && approvedMethodology();
    ready.disabled = !canGrow;
    ready.textContent = canGrow ? 'Go to Grow' : 'Onboard first';
  }
  renderOnboardStatus();
}

function humanItems(items) {
  return (items || []).filter(item => String(item.provenance || '').startsWith('human'));
}

function seedItems(items) {
  return (items || []).filter(item => !String(item.provenance || '').startsWith('human'));
}

function renderOnboardStatus(message = '') {
  const target = document.getElementById('go-onboard-status');
  if (!target || !store) return;
  const sourceCount = reviewableCorpus().length;
  const method = approvedMethodology();
  renderOnboardButton(method);
  target.className = method ? 'item' : 'empty';
  if (message) {
    target.textContent = message;
    return;
  }
  if (method) {
    target.innerHTML = `<strong>Onboarded.</strong> <span class="muted">PHEO Grow is ready for this workflow.</span>`;
    return;
  }
  if (sourceCount) {
    target.textContent = `${sourceCount} connected source${sourceCount === 1 ? '' : 's'} ready. Add more if needed, then onboard the apprentice.`;
    return;
  }
  target.textContent = 'Connect sources and rules, then onboard the apprentice.';
}

function renderOnboardButton(method = approvedMethodology()) {
  const button = document.getElementById('onboard-button');
  if (!button) return;
  const hasNewInput = Boolean(value('corpus-text') || value('rules-text'));
  button.disabled = Boolean(method && !hasNewInput);
  button.textContent = method ? (hasNewInput ? 'Update onboarding' : 'Onboarded') : 'Onboard apprentice';
}

function renderCorpus() {
  const items = reviewableCorpus();
  const target = document.getElementById('corpus-list');
  if (!items.length) {
    target.className = 'list empty';
    target.textContent = 'No data yet. Add source material or choose a template.';
    return;
  }
  target.className = 'list';
  target.innerHTML = items.map(item => `
    <div class="item">
      <div class="section-head" style="margin-bottom:8px">
        <div>
          <div class="item-title">${escapeHtml(item.title)}</div>
          <div class="muted small">${escapeHtml(item.source_type || 'text')} · ${escapeHtml(sourceLabel(item))}</div>
        </div>
        ${canRemoveSource(item) ? `<button class="ghost" title="Remove source" onclick="removeSource('${escapeAttr(item.id)}')">×</button>` : '<span class="status blue">demo</span>'}
      </div>
      <div class="small" style="margin-top:8px">${escapeHtml(truncate(item.text, 220))}</div>
    </div>
  `).join('');
}

async function attachCorpus() {
  ensureWorkflow();
  const text = value('corpus-text');
  if (!text) throw new Error('Add corpus or source material first.');
  await api(`/v1/workflows/${workflow.id}/corpus`, {method: 'POST', body: JSON.stringify({items: [{
    source_type: 'text',
    title: value('corpus-title') || 'Corpus item',
    text,
    tags: ['source_truth']
  }]})});
  await hydrateWorkflow();
  toast('Source added. Onboard the apprentice when ready.');
}

async function loadSourceFiles() {
  const input = document.getElementById('source-files');
  if (!input || !input.files || !input.files.length) return;
  const chunks = [];
  for (const file of Array.from(input.files)) {
    const text = await file.text();
    chunks.push(`Source file: ${file.name}\\n${text}`);
  }
  const target = document.getElementById('corpus-text');
  target.value = [target.value, ...chunks].filter(Boolean).join('\\n\\n---\\n\\n');
  toast(`${input.files.length} file${input.files.length === 1 ? '' : 's'} added to the corpus box.`);
}

async function removeSource(sourceId) {
  if (!sourceId) return;
  await api(`/v1/corpus/${encodeURIComponent(sourceId)}`, {method: 'DELETE'});
  await hydrateWorkflow();
  toast('Source removed from this workflow.');
}

async function onboardApprentice(button = null) {
  ensureWorkflow();
  const corpusText = value('corpus-text');
  const rulesText = value('rules-text');
  if (!corpusText && !rulesText && !activeCorpus().length) throw new Error('Add corpus material, rules, or both.');
  const items = [];
  if (corpusText) {
    items.push({
      source_type: 'text',
      title: 'Workflow corpus',
      text: corpusText,
      tags: ['workflow_corpus']
    });
  }
  if (rulesText) {
    items.push({
      source_type: 'text',
      title: 'Workflow rules and criteria',
      text: rulesText,
      tags: ['workflow_rules']
    });
  }
  if (items.length) {
    const existing = new Set(activeCorpus().map(item => `${item.title}::${item.text}`));
    const fresh = items.filter(item => !existing.has(`${item.title}::${item.text}`));
    if (fresh.length) {
      await api(`/v1/workflows/${workflow.id}/corpus`, {method: 'POST', body: JSON.stringify({items: fresh})});
    }
  }
  if (button) {
    button.disabled = true;
    button.textContent = 'Onboarding...';
  }
  renderOnboardStatus('Onboarding apprentice. Reading sources and building the review method.');
  toast('Onboarding apprentice. Building the review method now.');
  await sleep(650);
  await api(`/v1/workflows/${workflow.id}/methodology/build`, {method: 'POST', body: '{}'});
  renderOnboardStatus('Review method drafted. Checking it against the connected sources.');
  await sleep(450);
  await api(`/v1/workflows/${workflow.id}/methodology`);
  await api(`/v1/workflows/${workflow.id}/methodology/approve`, {method: 'POST', body: JSON.stringify({
    author: 'local_browser_reviewer',
    note: 'Approved during PHEO Go onboarding.'
  })});
  await hydrateWorkflow();
  if (button) {
    button.disabled = false;
    button.textContent = 'Onboard apprentice';
  }
  renderOnboardStatus('Onboarded. PHEO Grow is ready when you are.');
  toast('Onboarding complete. Go to Grow when ready.');
}

async function attachStarterSources(kind) {
  ensureWorkflow();
  await clearTemplateSources(kind);
  let items = [];
  if (kind === 'medical') {
    items = MEDICAL_PAPER_CASES.map(paper => ({
      source_type: 'text',
      title: `${paper.id} · ${paper.title}`,
      text: `${paper.title}\\n${paper.pmcid}\\n\\n${paper.excerpt}`,
      tags: ['template_medical_pmc_oa', paper.id, paper.pmcid, `target_${paper.target || 'review'}`]
    }));
    setIfPresent('corpus-text', '');
    setIfPresent('rules-text', MEDICAL_REVIEW_RULES);
  } else {
    items = [
      {
        source_type: 'text',
        title: 'Finance receipt review rules',
        text: FINANCE_REVIEW_RULES,
        tags: ['template_finance_rules']
      },
      ...FINANCE_RECEIPT_CASES.map(item => ({
        source_type: 'text',
        title: `${item.id} · ${item.title}`,
        text: `${item.title}\\n${item.excerpt}`,
        tags: ['template_finance_receipt', item.id]
      }))
    ];
    setIfPresent('corpus-text', '');
    setIfPresent('rules-text', FINANCE_REVIEW_RULES);
  }
  await api(`/v1/workflows/${workflow.id}/corpus`, {method: 'POST', body: JSON.stringify({items})});
  await hydrateWorkflow();
}

async function clearTemplateSources(kind) {
  const templateTag = kind === 'medical' ? 'template_medical_pmc_oa' : 'template_finance_receipt';
  const rulesTag = kind === 'medical' ? '' : 'template_finance_rules';
  const targets = activeCorpus().filter(item => {
    const tags = item.tags || [];
    return tags.includes(templateTag) || (rulesTag && tags.includes(rulesTag));
  });
  for (const item of targets) {
    await api(`/v1/corpus/${encodeURIComponent(item.id)}`, {method: 'DELETE'});
  }
}

async function clearWorkflowSources(skipConfirm = false) {
  ensureWorkflow();
  if (!skipConfirm && activeCorpus().length && !confirm('Clear active source material for this workflow? Previous inactive rows remain in audit history, but new rules use only active sources.')) return false;
  await api(`/v1/workflows/${workflow.id}/corpus`, {method: 'DELETE'});
  await hydrateWorkflow();
  toast('Active sources cleared for this workflow.');
  return true;
}

async function useDemoFinancePolicy(confirmReplace = true) {
  ensureWorkflow();
  if (confirmReplace && activeCorpus().length && !confirm('Load the demo finance receipt policy for this workflow?')) return;
  await clearWorkflowSources(true);
  await api(`/v1/workflows/${workflow.id}/corpus`, {method: 'POST', body: JSON.stringify({items: [{
    source_type: 'text',
    title: 'Demo finance receipt review policy',
    text: DEMO_FINANCE_RECEIPT_POLICY,
    tags: ['demo_finance_receipt_policy']
  }]})});
  document.getElementById('corpus-title').value = 'Demo finance receipt review policy';
  document.getElementById('corpus-text').value = DEMO_FINANCE_RECEIPT_POLICY;
  await hydrateWorkflow();
  go(nextStep());
  toast('Demo finance receipt policy loaded. Review or edit it, then create rules.');
}

async function buildMethodology() {
  ensureWorkflow();
  if (!activeCorpus().length) throw new Error('Add at least one source first.');
  if (approvedMethodology() && !confirm('Create a new draft from the current source data? Outputs will wait for approval again.')) return;
  toast('Pheo is building review rules from the active source material.');
  await api(`/v1/workflows/${workflow.id}/methodology/build`, {method: 'POST', body: '{}'});
  await hydrateWorkflow();
  toast('Review rules drafted. Edit or approve them before scoring workflow outputs.');
}

async function approveMethodology() {
  ensureWorkflow();
  const methodology = store.methodology;
  if (!methodology) throw new Error('Create review rules first.');
  if (methodology.status === 'approved') {
    toast('Review rules are already approved.');
    renderMethodologyActions();
    return;
  }
  await api(`/v1/workflows/${workflow.id}/methodology`);
  await api(`/v1/workflows/${workflow.id}/methodology/approve`, {method: 'POST', body: JSON.stringify({
    author: 'local_browser_reviewer',
    note: 'Approved in local PHEO UI.'
  })});
  await hydrateWorkflow();
  toast('Review rules approved. Initial preference pairs were created.');
}

function renderMethodologyActions() {
  const target = document.getElementById('methodology-actions');
  if (!target) return;
  const methodology = store && store.methodology;
  if (!methodology) {
    target.innerHTML = '<button class="blue" onclick="buildMethodology()">Build methodology</button>';
    return;
  }
  if (methodology.status === 'approved') {
    target.innerHTML = `
      <button class="blue" onclick="toggleRuleEditor()">Edit copy</button>
      <button class="ghost" disabled>Approved</button>
    `;
    return;
  }
  target.innerHTML = `
    <button class="blue" onclick="buildMethodology()">Rebuild methodology</button>
    <button class="blue" onclick="toggleRuleEditor()">Edit draft</button>
    <button class="primary" onclick="approveMethodology()">Approve</button>
  `;
}

function renderMethodology() {
  const target = document.getElementById('methodology-view');
  const methodology = store && store.methodology;
  renderMethodologyActions();
  if (!target) return;
  if (!methodology) {
    target.className = 'empty';
    target.textContent = activeCorpus().length
      ? 'Sources are connected. Build the methodology before Grow.'
      : 'Add corpus and rules, then onboard the apprentice.';
    return;
  }
  target.className = '';
  target.innerHTML = `
    <div class="method-box">
      <div class="item" style="margin-bottom:12px">
        <div class="tiny muted">Task</div>
        <p>${escapeHtml(publicText((workflow && workflow.objective) || '')) || '<span class="muted">No task was supplied; rules may be source-generic.</span>'}</p>
      </div>
      <div class="section-head" style="margin-bottom:10px">
        <div>
          <h3>Review rules</h3>
          <p>${escapeHtml(publicText(methodology.summary || 'No summary available.'))}</p>
        </div>
        <span class="status ${methodology.status === 'approved' ? '' : 'amber'}">${escapeHtml(methodology.status)}</span>
      </div>
      <div class="grid-2">
        <div>
          <h3>Must check</h3>
          ${list((methodology.rules || []).map(publicText))}
        </div>
        <div>
          <h3>Must not do</h3>
          ${list((methodology.avoid || []).map(publicText))}
        </div>
      </div>
      <div id="rule-editor" class="hidden" style="margin-top:14px">
        <h3>Edit rules</h3>
        <p class="muted small">Saving edits creates a draft. Approve the edited rules before reviewing more workflow outputs.</p>
        <label>Summary</label>
        <textarea id="edit-method-summary">${escapeHtml(publicText(methodology.summary || ''))}</textarea>
        <label>Must check, one rule per line</label>
        <textarea id="edit-method-rules">${escapeHtml((methodology.rules || []).map(publicText).join('\\n'))}</textarea>
        <label>Must not do, one rule per line</label>
        <textarea id="edit-method-avoid">${escapeHtml((methodology.avoid || []).map(publicText).join('\\n'))}</textarea>
        <div class="actions compact" style="margin-top:10px">
          <button class="primary" onclick="saveMethodologyEdits()">Save draft</button>
          <button onclick="toggleRuleEditor(false)">Cancel</button>
        </div>
      </div>
      ${renderMethodologyAudit(store.methodology_events || [])}
    </div>
  `;
}

function toggleRuleEditor(force) {
  const node = document.getElementById('rule-editor');
  if (!node) return;
  const shouldOpen = force === undefined ? node.classList.contains('hidden') : force;
  node.classList.toggle('hidden', !shouldOpen);
}

async function saveMethodologyEdits() {
  ensureWorkflow();
  await api(`/v1/workflows/${workflow.id}/methodology/update`, {method: 'POST', body: JSON.stringify({
    summary: value('edit-method-summary'),
    rules: linesFromTextarea('edit-method-rules'),
    avoid: linesFromTextarea('edit-method-avoid'),
    author: 'local_browser_reviewer',
    note: 'Edited in local PHEO UI.'
  })});
  await hydrateWorkflow();
  toast('Edited rules saved as draft. Approve them before reviewing new outputs.');
}

function renderMethodologyAudit(events) {
  if (!events.length) return '';
  return `
    <h3>Audit trail</h3>
    <div class="list tight">
      ${events.slice(0, 6).map(event => `
        <div class="item">
          <strong>${escapeHtml(labelFor(event.event_type || 'event'))}</strong>
          <p class="muted small">${escapeHtml(event.created_at || '')} · ${escapeHtml(publicActor(event.actor || 'unknown'))}</p>
          ${event.note ? `<p class="small">${escapeHtml(publicText(event.note))}</p>` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

async function createRun() {
  ensureWorkflow();
  if (!approvedMethodology()) throw new Error('Onboard apprentice first.');
  const generator = value('generator-label') || 'external_workflow';
  const candidates = [1, 2, 3]
    .map(index => value('candidate-' + index))
    .filter(Boolean)
    .map(output => ({output, generator}));
  if (!candidates.length) throw new Error('Paste at least one output to review.');
  const point = await ensureReviewPoint();
  const packet = await api(`/v1/stores/${workflow.id}/review-points/${encodeURIComponent(point.name)}/observations`, {method: 'POST', body: JSON.stringify({
    output: candidates[0].output,
    context: {goal: value('task-goal') || 'Review workflow output'},
    source: {connector: 'manual_capture', generator},
    candidates,
    mode: candidates.length === 1 ? 'kernel' : 'explicit_capture',
    use_memory: true
  })});
  reviewPacket = packet;
  currentRun = packet.run;
  await hydrateWorkflow();
  reviewPacket = packet;
  currentRun = packet.run;
  renderReviewPacketResults(packet);
  toast('Review case created. Pick what you would trust and explain why.');
}

function fillDemoReceiptOutputs() {
  document.getElementById('task-goal').value = 'Review finance receipt FIN-1007 before any payment-related action.';
  document.getElementById('generator-label').value = 'demo_finance_agent';
  DEMO_RECEIPT_OUTPUTS.forEach((text, index) => {
    const node = document.getElementById('candidate-' + (index + 1));
    if (node) node.value = text;
  });
  toast('Demo receipt outputs loaded. Score them, then capture your judgment.');
}

async function callEndpoint() {
  ensureWorkflow();
  if (!approvedMethodology()) throw new Error('Onboard apprentice first.');
  const endpointUrl = value('endpoint-url');
  const apiKey = value('endpoint-key');
  const model = value('endpoint-model');
  const objectText = value('customer-object');
  const sourceContext = selectedSourceContextText();
  const goal = [
    value('task-goal') || 'Create a workflow output for human review.',
    sourceContext ? `Connected sources:\\n${sourceContext}` : '',
    objectText ? `Object to review:\\n${objectText}` : ''
  ].filter(Boolean).join('\\n\\n');
  if (!endpointUrl || !apiKey || !model) throw new Error('Endpoint URL, API key, and model are required.');
  const point = await ensureReviewPoint();
  toast('Calling endpoint locally, then scoring outputs.');
  const packet = await api(`/v1/stores/${workflow.id}/review-points/${encodeURIComponent(point.name)}/endpoint-observations`, {method: 'POST', body: JSON.stringify({
    endpoint_url: endpointUrl,
    api_key: apiKey,
    model,
    task: {goal, connected_sources: selectedSourceTitles()},
    messages: [{role: 'user', content: goal}],
    use_memory: true
  })});
  reviewPacket = packet;
  currentRun = packet.run;
  await hydrateWorkflow();
  reviewPacket = packet;
  currentRun = packet.run;
  renderReviewPacketResults(packet);
  toast('Endpoint output captured. Review case is ready.');
}

async function importTraces() {
  ensureWorkflow();
  if (!approvedMethodology()) throw new Error('Onboard apprentice first.');
  const payloadText = value('trace-payload');
  if (!payloadText) throw new Error('Paste trace JSON first.');
  let payload;
  try {
    payload = JSON.parse(payloadText);
  } catch (error) {
    throw new Error('Trace payload must be valid JSON.');
  }
  toast('Importing trace outputs and scoring them.');
  const point = await ensureReviewPoint();
  const data = await api(`/v1/stores/${workflow.id}/review-points/${encodeURIComponent(point.name)}/trace-observations`, {method: 'POST', body: JSON.stringify({
    source_type: value('trace-source') || 'langsmith',
    payload,
    task: {goal: value('trace-goal') || value('task-goal') || 'Review traced workflow output'},
  })});
  await hydrateWorkflow();
  reviewPacket = (data.packets || [])[0] || null;
  currentRun = reviewPacket ? reviewPacket.run : null;
  if (reviewPacket) renderReviewPacketResults(reviewPacket);
  toast(`${(data.packets || []).length} trace review case${(data.packets || []).length === 1 ? '' : 's'} imported.`);
}

function renderRuns() {
  renderStarterReviewPanel();
  const target = document.getElementById('run-results');
  const packets = store && store.review_packets || [];
  const runs = store && store.runs || [];
  if (packets.length) {
    const enriched = packets.map(packet => {
      const run = runs.find(item => item.id === packet.run_id) || {};
      const candidates = run.candidates || [];
      const recommended = candidates.find(item => item.recommended) || candidates[0] || {};
      return {packet, run, candidates, recommended, bucket: bucketForReviewPacket(packet, recommended, run)};
    });
    target.innerHTML = `
      <div class="section-head">
        <div>
          <h3>PHEO Grow result</h3>
          <p class="muted small">${packets.length} observed item${packets.length === 1 ? '' : 's'}.</p>
        </div>
        <div class="actions compact">
          ${resultCountPill('Reviewed', enriched.filter(item => item.bucket === 'reviewed').length, '')}
          ${resultCountPill('Selected', enriched.filter(item => item.bucket === 'selected').length, '')}
          ${resultCountPill('Needs judgment', enriched.filter(item => item.bucket === 'review').length, 'amber')}
          ${resultCountPill('Not selected', enriched.filter(item => item.bucket === 'not_selected').length, 'blue')}
        </div>
      </div>
      ${renderResultsTable(enriched)}
    `;
    return;
  }
  if (!runs.length && !currentRun) {
    target.innerHTML = '<div class="empty">No Grow result yet. Run PHEO Grow on the connected starter set, call an endpoint, or paste outputs manually.</div>';
  }
}

function resultCountPill(label, count, klass) {
  return `<span class="status ${klass || ''}">${escapeHtml(label)} ${count}</span>`;
}

function renderResultsTable(items) {
  return `
    <div class="results-table-wrap">
      <table class="results-table">
        <thead>
          <tr>
            <th>Observed item</th>
            <th>PHEO result</th>
            <th>Quality</th>
            <th>Rules fit</th>
            <th>Human judgment</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${items.map(renderResultRow).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderResultRow(item) {
  const packet = item.packet || {};
  const recommended = item.recommended || {};
  const scores = recommended.scores || {};
  const url = packet.review_url || (packet.id ? `/review/${packet.id}` : '');
  const bucket = item.bucket || 'review';
  return `
    <tr>
      <td><div class="row-title">${escapeHtml(reviewItemTitle(item))}</div><div class="muted small">${escapeHtml(reviewItemSubline(item))}</div></td>
      <td>${resultPill(bucket)}</td>
      <td>${pct(scores.mean_score)}</td>
      <td>${pct(scores.methodology_fit)}</td>
      <td>${escapeHtml(judgmentState(item))}</td>
      <td>${url ? `<button onclick="window.open('${escapeAttr(url)}', '_blank')">Open</button>` : ''}</td>
    </tr>
  `;
}

function resultPill(bucket) {
  const klass = bucket === 'reviewed' ? 'reviewed' : bucket === 'review' ? 'review' : bucket === 'not_selected' ? 'not_selected' : '';
  return `<span class="result-pill ${klass}">${escapeHtml(resultLabel(bucket))}</span>`;
}

function resultLabel(bucket) {
  const labels = {
    selected: 'Selected',
    review: 'Needs judgment',
    not_selected: 'Not selected',
    reviewed: 'Reviewed'
  };
  return labels[bucket] || 'Needs judgment';
}

function reviewItemTitle(item) {
  const context = item.run && item.run.task && item.run.task.context || {};
  return context.title || context.case_id || item.packet.title || item.packet.id || 'Observed item';
}

function reviewItemSubline(item) {
  const context = item.run && item.run.task && item.run.task.context || {};
  const id = context.case_id || '';
  return id && String(reviewItemTitle(item)).indexOf(id) < 0 ? id : (item.packet.status === 'reviewed' ? 'judgment saved' : 'observed');
}

function judgmentState(item) {
  if ((item.packet || {}).status === 'reviewed') {
    const decision = decisionForPacket(item.packet, item.run);
    if (!decision) return 'Saved';
    const action = decision.action || 'approve';
    const author = decision.author_id || 'reviewer';
    const when = decision.created_at ? new Date(decision.created_at).toLocaleString() : '';
    return `${action} · ${author}${when ? ` · ${when}` : ''}`;
  }
  if (item.bucket === 'review') return 'Requested';
  return 'Optional';
}

function decisionForPacket(packet, run) {
  const runId = (run && run.id) || (packet && packet.run_id);
  if (!runId || !store) return null;
  return (store.decisions || []).find(item => item.run_id === runId) || null;
}

function renderBucket(title, subtitle, items) {
  return `
    <div class="bucket">
      <h3>${escapeHtml(title)} <span class="status ${title === 'Needs judgment' ? 'amber' : title === 'Not selected' ? 'blue' : ''}">${items.length}</span></h3>
      <p class="muted small" style="margin-bottom:10px">${escapeHtml(subtitle)}</p>
      ${items.length ? items.map(renderBucketItem).join('') : '<div class="empty small">None yet.</div>'}
    </div>
  `;
}

function renderBucketItem(item) {
  const packet = item.packet || {};
  const recommended = item.recommended || {};
  const id = packet.id || '';
  const url = packet.review_url || (id ? `/review/${id}` : '');
  const label = packet.title || packet.review_point_name || packet.review_point || id || 'Review item';
  const mean = pct((recommended.scores || {}).mean_score);
  return `
    <div class="item">
      <div class="item-title">${escapeHtml(labelForReviewItem(label))}</div>
      <div class="muted small">${escapeHtml(recommendedIntent(recommended))} · ${mean}</div>
      ${url ? `<button style="margin-top:8px" onclick="window.open('${escapeAttr(url)}', '_blank')">Open</button>` : ''}
    </div>
  `;
}

function bucketForReviewPacket(packet, recommended) {
  if (packet && packet.status === 'reviewed') return 'reviewed';
  const run = arguments.length > 2 ? arguments[2] : {};
  const target = run && run.task && run.task.context && run.task.context.target_bucket;
  if (['selected', 'review', 'not_selected'].includes(target)) return target;
  const text = `${recommended && recommended.output || ''}`.toLowerCase();
  const score = Number((recommended && recommended.scores || {}).mean_score || 0);
  if (text.includes('exclude') || text.includes('not include') || text.includes('keep out')) return 'not_selected';
  if (text.includes('hold') || text.includes('review') || text.includes('escalate') || score < 0.74) return 'review';
  return 'selected';
}

function recommendedIntent(candidate) {
  const text = `${candidate && candidate.output || ''}`.toLowerCase();
  if (text.includes('exclude') || text.includes('not include') || text.includes('keep out')) return 'not selected';
  if (text.includes('hold') || text.includes('review') || text.includes('escalate')) return 'needs judgment';
  return 'selected';
}

function starterReviewSet() {
  if (!workflow) return [];
  const key = `${workflow.name || ''} ${workflow.skill || ''} ${workflow.domain || ''}`.toLowerCase();
  const sourceItems = activeCorpus().filter(isReviewableSource).map(sourceToReviewCase);
  if (sourceItems.length) {
    if (!growSourceSelectionTouched) return sourceItems;
    return sourceItems.filter(item => selectedGrowSourceIds.has(item.source_id));
  }
  if (key.includes('medical') || key.includes('life_sciences')) return MEDICAL_PAPER_CASES;
  if (key.includes('finance') || key.includes('receipt')) return FINANCE_RECEIPT_CASES;
  return [];
}

function isReviewableSource(item) {
  const tags = item.tags || [];
  const title = `${item.title || ''}`.toLowerCase();
  if (tags.includes('workflow_rules') || tags.includes('template_finance_rules') || tags.includes('demo_finance_receipt_policy')) return false;
  if (title.includes('rules') || title.includes('criteria') || title.includes('policy')) return false;
  return Boolean((item.text || '').trim());
}

function sourceToReviewCase(item, index) {
  const title = item.title || `Connected source ${index + 1}`;
  const match = title.match(/^(P\\d+|R\\d+|AP-\\d+)/i);
  const target = (item.tags || []).find(tag => /^target_/.test(tag));
  return {
    id: match ? match[1] : `S${String(index + 1).padStart(3, '0')}`,
    title,
    excerpt: item.text || '',
    source_id: item.id,
    pmcid: (item.tags || []).find(tag => /^PMC/i.test(tag)) || '',
    target: target ? target.replace(/^target_/, '') : ''
  };
}

function starterReviewKind() {
  const set = starterReviewSet();
  if (!set.length) return '';
  const key = `${workflow.name || ''} ${workflow.skill || ''} ${workflow.domain || ''}`.toLowerCase();
  return key.includes('medical') || key.includes('life_sciences') ? 'papers' : 'receipts';
}

function renderGrowSourcePicker() {
  const target = document.getElementById('grow-source-picker');
  if (!target) return;
  const sources = reviewableCorpus();
  if (!sources.length) {
    target.className = 'source-picker empty';
    target.textContent = 'No connected source data yet.';
    return;
  }
  target.className = 'source-picker';
  const allSelectedByDefault = !growSourceSelectionTouched;
  target.innerHTML = sources.map(item => {
    const checked = allSelectedByDefault || selectedGrowSourceIds.has(item.id);
    return `
      <label class="source-option">
        <input type="checkbox" ${checked ? 'checked' : ''} onchange="toggleGrowSource('${escapeAttr(item.id)}', this.checked)">
        <span>
          <strong>${escapeHtml(item.title || 'Connected source')}</strong>
          <span class="muted small" style="display:block">${escapeHtml(sourceLabel(item))}</span>
        </span>
      </label>
    `;
  }).join('');
}

function pruneSelectedGrowSources() {
  const ids = new Set(reviewableCorpus().map(item => item.id));
  selectedGrowSourceIds = new Set(Array.from(selectedGrowSourceIds).filter(id => ids.has(id)));
  if (!selectedGrowSourceIds.size && !reviewableCorpus().length) growSourceSelectionTouched = false;
}

function toggleGrowSource(sourceId, checked) {
  const sources = reviewableCorpus();
  if (!growSourceSelectionTouched) {
    selectedGrowSourceIds = new Set(sources.map(item => item.id));
    growSourceSelectionTouched = true;
  }
  if (checked) {
    selectedGrowSourceIds.add(sourceId);
  } else {
    selectedGrowSourceIds.delete(sourceId);
  }
  renderStarterReviewPanel();
}

function selectAllGrowSources() {
  selectedGrowSourceIds = new Set(reviewableCorpus().map(item => item.id));
  growSourceSelectionTouched = true;
  renderStarterReviewPanel();
}

function clearGrowSourceSelection() {
  selectedGrowSourceIds = new Set();
  growSourceSelectionTouched = true;
  renderStarterReviewPanel();
}

function selectedSourceItems() {
  const sources = reviewableCorpus();
  if (!growSourceSelectionTouched) return sources;
  return sources.filter(item => selectedGrowSourceIds.has(item.id));
}

function selectedSourceTitles() {
  return selectedSourceItems().map(item => item.title || 'Connected source');
}

function selectedSourceContextText(limit = 6) {
  return selectedSourceItems().slice(0, limit).map((item, index) => {
    const title = item.title || `Source ${index + 1}`;
    return `${title}\\n${truncate(item.text || '', 700)}`;
  }).join('\\n\\n---\\n\\n');
}

function renderStarterReviewPanel() {
  const target = document.getElementById('starter-review-panel');
  renderGrowSourcePicker();
  if (!target) return;
  const set = starterReviewSet();
  if (!set.length) {
    target.innerHTML = '<div class="empty">Observe a connected source set, endpoint output, trace, pasted output, or business object.</div>';
    return;
  }
  const kind = starterReviewKind();
  const ready = approvedMethodology();
  target.innerHTML = `
      <div class="item">
      <div class="section-head">
        <div>
          <h3>Observe selected ${kind}</h3>
          <p class="muted small">${set.length} item${set.length === 1 ? '' : 's'} selected.</p>
        </div>
        <button class="primary" ${ready ? '' : 'disabled'} onclick="startStarterReview(this)">${ready ? 'Run PHEO Grow' : 'Onboard first'}</button>
      </div>
    </div>
  `;
}

async function startStarterReview(button = null) {
  ensureWorkflow();
  if (!approvedMethodology()) throw new Error('Onboard apprentice first.');
  const set = starterReviewSet();
  if (!set.length) throw new Error('No starter review set for this workflow.');
  const point = await ensureReviewPoint();
  if (button) {
    button.disabled = true;
    button.textContent = 'Running...';
  }
  toast(`Running PHEO Grow on ${set.length} ${starterReviewKind()}.`);
  for (const item of set) {
    const isMedical = starterReviewKind() === 'papers';
    const candidates = isMedical ? medicalCandidates(item) : financeCandidates(item);
    await api(`/v1/stores/${workflow.id}/review-points/${encodeURIComponent(point.name)}/observations`, {method: 'POST', body: JSON.stringify({
      output: candidates[0].output,
      context: {case_id: item.id, title: item.title, source_text: item.excerpt, target_bucket: item.target || ''},
      source: {connector: isMedical ? 'starter_pmc_oa_corpus' : 'starter_finance_receipts', case_id: item.id},
      candidates,
      mode: 'explicit_capture',
      use_memory: true
    })});
  }
  await hydrateWorkflow();
  go('grow');
  toast('PHEO Grow finished. Buckets are ready.');
}

function medicalCandidates(item) {
  return [
    {generator: 'medical_starter', output: `Include ${item.id}: ${item.title}\\n\\nReason: The paper is breast-cancer specific and appears to contain extractable scientific evidence.\\n\\nEvidence: ${item.excerpt}`},
    {generator: 'medical_starter', output: `Hold ${item.id} for review: ${item.title}\\n\\nReason: Breast-cancer relevance is present, but the reviewer should confirm extractable evidence and synthesis utility.\\n\\nEvidence: ${item.excerpt}`},
    {generator: 'medical_starter', output: `Exclude ${item.id}: ${item.title}\\n\\nReason: Do not include unless the paper has direct review-context evidence rather than background signal only.\\n\\nEvidence: ${item.excerpt}`}
  ];
}

function financeCandidates(item) {
  return [
    {generator: 'finance_starter', output: `Clear ${item.id}: ${item.title}\\n\\nReason: The receipt appears reviewable if approval and support are confirmed.\\n\\nContext: ${item.excerpt}`},
    {generator: 'finance_starter', output: `Hold ${item.id}: ${item.title}\\n\\nReason: Do not release until approval clarity, support package, and duplicate risk are checked.\\n\\nContext: ${item.excerpt}`},
    {generator: 'finance_starter', output: `Escalate ${item.id}: ${item.title}\\n\\nReason: Escalate if approval is unclear, support is missing, or duplicate risk is present.\\n\\nContext: ${item.excerpt}`}
  ];
}

function renderReviewPacketResults(packet) {
  const target = document.getElementById('run-results');
  const candidates = packet.candidates || [];
  if (!candidates.length) return;
  const recommended = packet.recommended || candidates.find(item => item.recommended) || candidates[0];
  const reviewUrl = packet.packet && packet.packet.review_url ? packet.packet.review_url : '';
  target.innerHTML = `
    <div class="section-head">
      <div>
        <h2>Review case</h2>
        <p class="muted">Recommended output ${recommended.index + 1}, but the human review is the source of truth.</p>
      </div>
      <div class="actions">
        ${reviewUrl ? `<button onclick="window.open('${escapeAttr(reviewUrl)}', '_blank')">Open review page</button>` : ''}
        <select id="selected-index" onchange="renderQualityPanel('quality-panel', currentCandidates(), Number(value('selected-index')))">
          ${candidates.map(item => `<option value="${item.index}">Output ${item.index + 1}</option>`).join('')}
        </select>
        <button class="primary" onclick="captureDecision()">Capture review</button>
      </div>
    </div>
    <div id="quality-panel" style="margin-bottom:14px"></div>
    <label>Decision reason</label>
    <input id="decision-reason" value="Most grounded and reviewable.">
    <div class="grid-3" style="margin-top:14px">
      ${candidates.map(candidate => renderReviewCandidate(candidate, 'selected-index', 'quality-panel')).join('')}
    </div>
  `;
  const select = document.getElementById('selected-index');
  if (select) select.value = String(recommended.index);
  renderQualityPanel('quality-panel', candidates, recommended.index ?? 0);
}

function renderRunResults(run) {
  const target = document.getElementById('run-results');
  const candidates = run.candidates || [];
  if (!candidates.length) return;
  const recommended = candidates.find(item => item.recommended) || candidates[0];
  target.innerHTML = `
    <div class="section-head">
      <div>
        <h2>Scored outputs</h2>
        <p class="muted">Recommended output ${recommended.index + 1}, but the human review is the source of truth.</p>
      </div>
      <div class="actions">
        <select id="selected-index">
          ${candidates.map(item => `<option value="${item.index}">Output ${item.index + 1}</option>`).join('')}
        </select>
        <button class="primary" onclick="captureDecision()">Capture decision</button>
      </div>
    </div>
    <label>Decision reason</label>
    <input id="decision-reason" value="Most grounded and reviewable.">
    <div class="grid-3" style="margin-top:14px">
      ${candidates.map(renderCandidate).join('')}
    </div>
  `;
  const select = document.getElementById('selected-index');
  if (select) select.value = String(recommended.index);
}

function renderCandidate(candidate) {
  const scores = candidate.scores || {};
  const mean = pct(scores.mean_score);
  return `
    <div class="candidate">
      <div class="candidate-header">
        <strong>Output ${candidate.index + 1}</strong>
        <span class="status ${candidate.recommended ? '' : 'amber'}">${candidate.recommended ? 'Recommended' : 'Rank ' + (candidate.rank || '-')} · ${mean}</span>
      </div>
      <div class="candidate-body">${escapeHtml(candidate.output)}</div>
      <div class="pad">
        <div class="scores">
          ${scoreRow('Rules fit', scores.methodology_fit)}
          ${scoreRow('Grounding', scores.grounding)}
          ${scoreRow('Action', scores.actionability)}
          ${scoreRow('Context', scores.context_sensitivity)}
          ${scoreRow('Safety', scores.safety)}
          ${scoreRow('Clarity', scores.clarity)}
        </div>
        ${scoreExplanation(scores)}
      </div>
    </div>
  `;
}

async function captureDecision() {
  if (reviewPacket && reviewPacket.packet) {
    await api(`/v1/review-packets/${reviewPacket.packet.id}/reviews`, {method: 'POST', body: JSON.stringify({
      selected_index: Number(value('selected-index')),
      action: 'approve',
      reason: value('decision-reason') || 'Selected by human reviewer.'
    })});
  } else {
    if (!currentRun) throw new Error('Score outputs first.');
    await api(`/v1/runs/${currentRun.id}/decisions`, {method: 'POST', body: JSON.stringify({
      selected_index: Number(value('selected-index')),
      action: 'approve',
      reason: value('decision-reason') || 'Selected by human reviewer.'
    })});
  }
  await hydrateWorkflow();
  go('decisions');
  toast('Review captured. This workflow now has reusable decision memory.');
}

async function loadPack() {
  ensureWorkflow();
  await renderPack(true);
}

async function renderPack(showRaw) {
  if (!workflow) return;
  const pack = await api(`/v1/workflows/${workflow.id}/memory-pack`);
  const artifacts = pack.artifacts || {};
  const readiness = pack.readiness || {};
  const summary = document.getElementById('pack-summary');
  summary.innerHTML = `
    <div class="item">
      <h3>Readiness</h3>
      <p><b>${readiness.score || 0}/100</b> · ${escapeHtml(readiness.label || 'seed_data')}</p>
      <p class="muted small">${escapeHtml(readiness.summary || '')}</p>
    </div>
    <div class="item">
      <h3>Strengths</h3>
      ${list((pack.critique && pack.critique.strengths) || [])}
    </div>
    <div class="item">
      <h3>Next steps</h3>
      ${list((pack.critique && pack.critique.next_steps) || [])}
    </div>
  `;
  renderArtifactExplain(artifacts);
  renderDataViewer(pack);
  document.getElementById('pack-output').textContent = JSON.stringify(pack, null, 2);
}

function renderArtifactExplain(artifacts) {
  const target = document.getElementById('artifact-explain');
  if (!target) return;
  const humanPairs = humanItems(artifacts.preference_pairs || []);
  const seedPairs = seedItems(artifacts.preference_pairs || []);
  const humanDecisions = humanItems(artifacts.decision_log || []);
  const cards = [
    {
      title: 'Human preference pairs',
      count: humanPairs.length,
      copy: 'Pairs created from reviewer choices. One reviewed item can create multiple pairs.'
    },
    {
      title: 'Seed rule pairs',
      count: seedPairs.length,
      copy: 'Bootstrap pairs created from approved rules. These are not human review decisions.'
    },
    {
      title: 'Released examples',
      count: (artifacts.review_examples || []).length,
      copy: 'Human-reviewed examples that show what good output looks like in this workflow.'
    },
    {
      title: 'Check cases',
      count: (artifacts.check_cases || []).length,
      copy: 'Replayable checks from observed items, source rules, and review outcomes.'
    },
    {
      title: 'Human decision log',
      count: humanDecisions.length,
      copy: 'Who reviewed what, why they chose it, and when the decision was captured.'
    },
  ];
  target.innerHTML = cards.map(card => `
    <div class="artifact-card">
      <span class="muted tiny">${escapeHtml(card.title)}</span>
      <b>${card.count}</b>
      <p class="muted small">${escapeHtml(card.copy)}</p>
    </div>
  `).join('');
}

async function downloadPack() {
  ensureWorkflow();
  const pack = await api(`/v1/workflows/${workflow.id}/memory-pack`);
  downloadText('pref_store_memory.json', JSON.stringify(pack, null, 2), 'application/json');
}

async function downloadJsonl(kind) {
  ensureWorkflow();
  const response = await fetch(`/v1/export/${kind}?workflow=${encodeURIComponent(workflow.id)}`);
  if (!response.ok) throw new Error('Export failed.');
  const text = await response.text();
  const names = {
    preferences: 'preference_pairs.jsonl',
    examples: 'review_examples.jsonl',
    'checks': 'check_cases.jsonl'
  };
  downloadText(names[kind] || `${kind}.jsonl`, text, 'application/jsonl');
}

function go(step) {
  goStep(step).catch(showError);
}

async function goStep(step) {
  if (step === 'grow' && (!activeCorpus().length || !approvedMethodology())) {
    toast('Finish PHEO Go first: onboard source material and rules.', true);
    step = 'go';
  }
  activeStep = step;
  document.querySelectorAll('.panel').forEach(panel => panel.classList.add('hidden'));
  document.getElementById('panel-' + step).classList.remove('hidden');
  document.querySelectorAll('button.step').forEach(button => button.classList.remove('active'));
  const stepButton = document.getElementById('step-' + step);
  if (stepButton) stepButton.classList.add('active');
  if (step === 'go') {
    renderOnboardStatus();
  }
  if (step === 'grow' && workflow) {
    await hydrateWorkflow();
  }
}

function nextStep() {
  if (!activeCorpus().length || !approvedMethodology()) return 'go';
  if (!(store.review_packets || store.runs || []).length) return 'grow';
  return 'decisions';
}

async function ensureReviewPoint() {
  ensureWorkflow();
  let points = store && store.review_points || [];
  const name = reviewPointName();
  let point = points.find(item => item.active && item.name === name) || points.find(item => item.name === name) || points.find(item => item.active) || points[0];
  if (point) return point;
  const data = await api(`/v1/stores/${workflow.id}/review-points`, {method: 'POST', body: JSON.stringify({
    name,
    description: workflow.objective || `Review outputs for ${workflow.name}.`,
    dimensions: ['rules_fit', 'grounding', 'actionability', 'context', 'safety', 'clarity'],
    human_review: 'required',
    branching: 'kernel'
  })});
  await hydrateWorkflow();
  return data.review_point;
}

function reviewPointName() {
  const base = workflow && (workflow.skill || workflow.domain || workflow.name) || 'workflow';
  return `${slugify(base)}_review`;
}

function slugify(value) {
  const slug = String(value || 'workflow').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return slug || 'workflow';
}

function currentCandidates() {
  return reviewPacket && reviewPacket.candidates || currentRun && currentRun.candidates || [];
}

function selectCandidate(index, selectId, qualityPanelId) {
  const select = document.getElementById(selectId);
  if (select) select.value = String(index);
  renderQualityPanel(qualityPanelId, currentCandidates(), index);
}

function renderQualityPanel(targetId, candidates, selectedIndex) {
  const target = document.getElementById(targetId);
  if (!target || !candidates || !candidates.length) return;
  const selected = candidates.find(item => Number(item.index) === Number(selectedIndex)) || candidates[0];
  const recommended = candidates.find(item => item.recommended) || candidates[0];
  const scores = selected.scores || {};
  target.innerHTML = `
    <div class="quality-layout">
      <div class="radar-card">
        ${radarSvg(scores)}
        <div class="quality-score">
          <span>${selected.index === recommended.index ? 'Recommended quality' : 'Selected quality'}</span>
          <strong>${pct(candidateMean(selected))}</strong>
        </div>
      </div>
      <div>
        <div class="section-head" style="margin-bottom:8px">
          <div>
            <h3>Quality radar</h3>
            <p class="muted small">Review scores stored with output ${selected.index + 1}.</p>
          </div>
          <span class="status ${selected.recommended ? '' : 'amber'}">${selected.recommended ? 'Recommended' : 'Rank ' + (selected.rank || '-')}</span>
        </div>
        <div class="scores">
          ${scoreRow('Rules fit', scores.methodology_fit)}
          ${scoreRow('Grounding', scores.grounding)}
          ${scoreRow('Action', scores.actionability)}
          ${scoreRow('Context', scores.context_sensitivity)}
          ${scoreRow('Safety', scores.safety)}
          ${scoreRow('Clarity', scores.clarity)}
        </div>
        ${scoreExplanation(scores)}
      </div>
    </div>
  `;
  document.querySelectorAll('[data-candidate-index]').forEach(node => {
    node.classList.toggle('selected', Number(node.dataset.candidateIndex) === Number(selected.index));
  });
}

const RADAR_AXES = [
  ['Rules', 'methodology_fit'],
  ['Ground', 'grounding'],
  ['Action', 'actionability'],
  ['Context', 'context_sensitivity'],
  ['Safety', 'safety'],
  ['Clarity', 'clarity'],
];

function radarSvg(scores) {
  const center = 90;
  const radius = 62;
  const ring = scale => RADAR_AXES.map((_, index) => radarPoint(index, radius * scale, center)).join(' ');
  const shape = RADAR_AXES.map((axis, index) => radarPoint(index, radius * Math.max(0, Math.min(1, Number(scores[axis[1]] || 0))), center)).join(' ');
  const spokes = RADAR_AXES.map((_, index) => {
    const point = radarPoint(index, radius, center).split(',');
    return `<line x1="${center}" y1="${center}" x2="${point[0]}" y2="${point[1]}"></line>`;
  }).join('');
  const labels = RADAR_AXES.map((axis, index) => {
    const point = radarPoint(index, 78, center).split(',');
    return `<text x="${point[0]}" y="${point[1]}" text-anchor="middle" dominant-baseline="middle">${escapeHtml(axis[0])}</text>`;
  }).join('');
  return `
    <svg class="radar-svg" viewBox="0 0 180 180" role="img" aria-label="Quality radar">
      <g class="radar-grid">
        <polygon points="${ring(1)}"></polygon>
        <polygon points="${ring(.66)}"></polygon>
        <polygon points="${ring(.33)}"></polygon>
        ${spokes}
      </g>
      <polygon class="radar-shape" points="${shape}"></polygon>
      <g class="radar-labels">${labels}</g>
    </svg>
  `;
}

function radarPoint(index, radius, center) {
  const angle = (Math.PI * 2 * index) / RADAR_AXES.length - Math.PI / 2;
  return `${center + Math.cos(angle) * radius},${center + Math.sin(angle) * radius}`;
}

function candidateMean(candidate) {
  const scores = candidate && candidate.scores || {};
  if (typeof scores.mean_score === 'number') return scores.mean_score;
  const values = RADAR_AXES.map(axis => Number(scores[axis[1]] || 0)).filter(Number.isFinite);
  if (!values.length) return 0;
  return values.reduce((sum, item) => sum + item, 0) / values.length;
}

function renderDataViewer(pack) {
  const target = document.getElementById('data-viewer');
  if (!target) return;
  const artifacts = pack.artifacts || {};
  const sections = {
    sources: artifacts.source_corpus || [],
    packets: artifacts.review_packets || [],
    candidates: artifacts.candidate_quality || [],
    decisions: artifacts.decision_log || [],
    pairs: artifacts.preference_pairs || [],
    graph: pack.workflow_graph || {},
  };
  if (!sections[activeDataTable]) activeDataTable = 'candidates';
  const tabs = Object.keys(sections).map(key => (
    `<button class="${key === activeDataTable ? 'active' : ''}" onclick="activeDataTable='${key}'; renderDataViewer(window.lastPack)">${dataTabLabel(key, sections[key])}</button>`
  )).join('');
  window.lastPack = pack;
  target.innerHTML = `
    <h3 style="margin-top:20px">Data viewer</h3>
    <p class="muted small">Seed rows come from approved rules. Human rows come from reviewed cases.</p>
    <div class="data-tabs">${tabs}</div>
    ${activeDataTable === 'graph' ? graphView(pack) : tableFor(activeDataTable, sections[activeDataTable])}
  `;
}

function dataTabLabel(key, value) {
  if (key === 'graph') return 'Workflow Graph';
  const labels = {
    decisions: 'All Decision Rows',
    pairs: 'All Preference Pairs',
    packets: 'Review Cases',
  };
  return `${labels[key] || labelFor(key)} · ${(value || []).length}`;
}

function graphView(pack) {
  const artifacts = pack.artifacts || {};
  const graph = pack.workflow_graph || {};
  const humanDecisions = humanItems(artifacts.decision_log || []);
  const humanPairs = humanItems(artifacts.preference_pairs || []);
  const seedPairs = seedItems(artifacts.preference_pairs || []);
  const nodes = [
    ['Source data', (artifacts.source_corpus || []).length, 'Policies, examples, evidence, and notes.'],
    ['Review rules', pack.methodology ? 1 : 0, 'Approved operating logic for this workflow.'],
    ['Review points', (artifacts.review_points || []).length, 'Where outputs become reviewable.'],
    ['Review cases', (artifacts.review_packets || []).length, 'Captured outputs with candidates and scores.'],
    ['Human decisions', humanDecisions.length, 'Approve, edit, reject, or escalate with reasons.'],
    ['Preference pairs', humanPairs.length, `${seedPairs.length} method seed pairs kept separate.`],
  ];
  return `
    <div class="workflow-graph">
      <div class="graph-row">
        ${nodes.map(node => `
          <div class="graph-node">
            <span class="muted tiny">${escapeHtml(node[0])}</span>
            <strong>${escapeHtml(String(node[1]))}</strong>
            <p class="muted small">${escapeHtml(node[2])}</p>
          </div>
        `).join('')}
      </div>
      <p class="muted small" style="margin-top:12px">Exported graph: ${escapeHtml(graph.schema || 'pheo.workflow_graph.v1')}. The download includes full lineage; this view keeps the workflow readable.</p>
    </div>
  `;
}

function tableFor(kind, rows) {
  if (!rows || !rows.length) return '<div class="empty">No rows yet.</div>';
  const normalized = rows.map(flattenRow);
  const preferred = {
    sources: ['title', 'source_type', 'tags', 'active', 'created_at'],
    packets: ['status', 'review_url', 'created_at', 'updated_at'],
    candidates: ['output', 'generator', 'rank', 'recommended', 'scores'],
    decisions: ['action', 'reason', 'selected_index', 'author_id', 'created_at'],
    pairs: ['prompt', 'chosen_output', 'rejected_output', 'weight', 'provenance'],
  };
  const available = new Set(normalized.flatMap(row => Object.keys(row)));
  const columns = (preferred[kind] || Array.from(available)).filter(column => available.has(column)).slice(0, 6);
  return `
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr>${columns.map(column => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead>
        <tbody>
          ${normalized.slice(0, 80).map(row => `<tr>${columns.map(column => `<td>${escapeHtml(formatCell(row[column]))}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function flattenRow(row) {
  const out = {};
  Object.entries(row || {}).forEach(([key, val]) => {
    if (val === null || val === undefined) {
      out[key] = '';
    } else if (typeof val === 'object') {
      out[key] = Array.isArray(val) ? val.map(formatCell).join(' | ') : JSON.stringify(val);
    } else {
      out[key] = val;
    }
  });
  return out;
}

function formatCell(value) {
  const text = publicText(String(value ?? ''));
  return text.length > 240 ? text.slice(0, 239) + '…' : text;
}

function publicText(value) {
  let text = String(value ?? '');
  const oldFocusLabel = 'methodology ' + 'signals';
  text = text.replace(new RegExp('\\\\s*Dominant ' + oldFocusLabel + ':[^.]*\\\\.', 'gi'), '');
  text = text.replace(new RegExp('Methodology ' + oldFocusLabel.split(' ')[1] + ':[^\\\\n]*', 'gi'), 'Review focus captured from source material.');
  text = text.replace(new RegExp('discovered ' + oldFocusLabel, 'gi'), 'source-specific review guidance');
  text = text.replace(new RegExp(oldFocusLabel, 'gi'), 'review guidance');
  text = text.replace(new RegExp('pheo-' + 'kernel', 'gi'), 'pheo');
  return text.replace(/\\s{2,}/g, ' ').trim();
}

function publicActor(value) {
  return publicText(value || 'unknown');
}

function labelFor(key) {
  if (key === 'packets') return 'Review Cases';
  if (key === 'pairs') return 'Preference Pairs';
  return key.replace(/_/g, ' ').replace(/\\b\\w/g, char => char.toUpperCase());
}

function labelForReviewItem(label) {
  const clean = String(label || 'Review item').replace(/^ap_exception_review$/i, 'Review item');
  return clean.length > 80 ? clean.slice(0, 77) + '...' : clean;
}

function activeCorpus() {
  return (store && store.corpus || []).filter(item => item.active);
}

function reviewableCorpus() {
  return activeCorpus().filter(isReviewableSource);
}

function sourceLabel(item) {
  const tags = item.tags || [];
  if (tags.includes('template_medical_pmc_oa')) return 'PMC OA demo paper';
  if (tags.includes('template_finance_receipt')) return 'demo receipt';
  return 'added source';
}

function canRemoveSource(item) {
  const tags = item.tags || [];
  return !(tags.includes('template_medical_pmc_oa') || tags.includes('template_finance_receipt'));
}

function approvedMethodology() {
  return store && store.methodology && store.methodology.status === 'approved';
}

function ensureWorkflow() {
  if (!workflow) throw new Error('Create or select a workflow first.');
}

function value(id) {
  const node = document.getElementById(id);
  return node ? node.value.trim() : '';
}

function setIfPresent(id, nextValue) {
  const node = document.getElementById(id);
  if (node && nextValue !== undefined && nextValue !== null) node.value = nextValue;
}

function linesFromTextarea(id) {
  return value(id).split('\\n').map(item => item.trim()).filter(Boolean);
}

function scoreRow(label, value) {
  const percent = pct(value);
  const number = Math.max(0, Math.min(100, Math.round((value || 0) * 100)));
  return `<div class="score-row"><span class="muted small">${label}</span><span class="bar"><i style="width:${number}%"></i></span><b>${percent}</b></div>`;
}

function scoreExplanation(scores) {
  const explanation = scores && scores.explanation || {};
  if (!explanation.summary) return '';
  const drivers = (explanation.weakest_dimensions || []).slice(0, 2);
  return `
    <div class="score-explain">
      <p><b>Why this score:</b> ${escapeHtml(explanation.summary)}</p>
      ${drivers.length ? `<ul>${drivers.map(item => `<li>${escapeHtml(item.label || item.dimension)}: ${escapeHtml(item.reason || '')}</li>`).join('')}</ul>` : ''}
    </div>
  `;
}

function pct(value) {
  if (value === undefined || value === null) return '-';
  return Math.round(value * 100) + '%';
}

function list(items) {
  if (!items || !items.length) return '<p class="muted small">None yet.</p>';
  return '<ul class="small">' + items.map(item => `<li>${escapeHtml(item)}</li>`).join('') + '</ul>';
}

function downloadText(filename, text, type) {
  const blob = new Blob([text], {type});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function toast(message) {
  const node = document.getElementById('toast');
  node.textContent = message;
  node.className = 'toast';
  setTimeout(() => node.classList.add('hidden'), 3600);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function showError(error) {
  const node = document.getElementById('toast');
  node.textContent = error.message || String(error);
  node.className = 'toast error';
  setTimeout(() => node.classList.add('hidden'), 5200);
}

window.addEventListener('error', event => showError(event.error || event.message));
window.addEventListener('unhandledrejection', event => showError(event.reason || event));

function truncate(text, limit) {
  text = (text || '').replace(/\\s+/g, ' ').trim();
  return text.length > limit ? text.slice(0, limit - 1) + '…' : text;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}
</script>
</body>
</html>"""
