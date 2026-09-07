#!/usr/bin/env node
import { spawn, spawnSync } from "node:child_process";
import { chmod, copyFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

const DEFAULT_APP_URL = "https://ai-music.168.107.34.175.sslip.io/";
const DEFAULT_API_BASE = "https://ai-music.168.107.34.175.sslip.io/api";
const DEFAULT_ENV_FILE = "/home/hong/.openclaw/ai-music.env";
const DEFAULT_CDP_PORT = "18800";
const DEFAULT_CHROME_PATH = "/opt/google/chrome/chrome";
const DEFAULT_USER_DATA_DIR = "/home/hong/.openclaw/browser/openclaw/user-data";

function parseArgs(argv) {
  const args = {
    appUrl: process.env.AIMP_APP_URL || DEFAULT_APP_URL,
    apiBase: process.env.AIMP_LOCAL_API_BASE || DEFAULT_API_BASE,
    envFile: process.env.AIMP_OPENCLAW_ENV_FILE || DEFAULT_ENV_FILE,
    cdpPort: process.env.CDP_PORT || DEFAULT_CDP_PORT,
    chromePath: process.env.OPENCLAW_CHROME_PATH || DEFAULT_CHROME_PATH,
    userDataDir: process.env.OPENCLAW_BROWSER_USER_DATA_DIR || DEFAULT_USER_DATA_DIR,
    launchBrowserIfNeeded: false,
    restartService: "",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = () => {
      const value = argv[index + 1];
      if (!value) throw new Error(`${arg} requires a value`);
      index += 1;
      return value;
    };

    if (arg === "--app-url") args.appUrl = next();
    else if (arg === "--api-base") args.apiBase = next();
    else if (arg === "--env-file") args.envFile = next();
    else if (arg === "--cdp-port") args.cdpPort = next();
    else if (arg === "--chrome-path") args.chromePath = next();
    else if (arg === "--user-data-dir") args.userDataDir = next();
    else if (arg === "--launch-browser-if-needed") args.launchBrowserIfNeeded = true;
    else if (arg === "--restart-service") args.restartService = next();
    else if (arg === "--help" || arg === "-h") {
      console.log(
        [
          "Usage: openclaw_refresh_api_cookie.mjs [options]",
          "",
          "Options:",
          "  --app-url URL            AI Music public app URL",
          "  --api-base URL           API base to write as AIMP_LOCAL_API_BASE",
          "  --env-file PATH          OpenClaw env file to update",
          "  --cdp-port PORT          OpenClaw browser CDP port",
          "  --chrome-path PATH       Chrome binary to launch if CDP is down",
          "  --user-data-dir PATH     OpenClaw browser profile directory",
          "  --launch-browser-if-needed",
          "                           Start headless Chrome briefly when CDP is down",
          "  --restart-service NAME   Restart this user systemd service if env changed",
        ].join("\n"),
      );
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function isCookieForHost(cookie, host) {
  const domain = String(cookie.domain || "").replace(/^\./, "");
  return domain === host || host.endsWith(`.${domain}`) || domain.endsWith(host);
}

async function callCdp(webSocketUrl, method, params = {}) {
  const ws = new WebSocket(webSocketUrl);
  let seq = 0;
  const pending = new Map();

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) {
      reject(new Error(`${message.error.message || "CDP error"} ${message.error.data || ""}`.trim()));
    } else {
      resolve(message.result);
    }
  });

  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });

  const send = (name, payload = {}) => {
    const id = ++seq;
    ws.send(JSON.stringify({ id, method: name, params: payload }));
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  };

  try {
    await send("Network.enable");
    return await send(method, params);
  } finally {
    ws.close();
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readTargets(cdpPort) {
  const targetsResponse = await fetch(`http://127.0.0.1:${cdpPort}/json/list`);
  if (!targetsResponse.ok) {
    throw new Error(`OpenClaw browser CDP returned ${targetsResponse.status}`);
  }
  return targetsResponse.json();
}

function launchHeadlessChrome({ appUrl, cdpPort, chromePath, userDataDir }) {
  return spawn(
    chromePath,
    [
      "--headless=new",
      `--remote-debugging-port=${cdpPort}`,
      `--user-data-dir=${userDataDir}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--disable-background-networking",
      "--disable-component-update",
      "--disable-features=Translate,MediaRouter",
      "--password-store=basic",
      appUrl,
    ],
    {
      detached: false,
      stdio: "ignore",
    },
  );
}

async function targetsWithOptionalLaunch(args) {
  try {
    return { targets: await readTargets(args.cdpPort), browserProcess: null };
  } catch (error) {
    if (!args.launchBrowserIfNeeded) {
      throw new Error(`OpenClaw browser CDP is not reachable on port ${args.cdpPort}: ${error.message}`);
    }
  }

  const browserProcess = launchHeadlessChrome(args);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await delay(500);
    try {
      return { targets: await readTargets(args.cdpPort), browserProcess };
    } catch {
      if (browserProcess.exitCode !== null) {
        throw new Error(`Headless Chrome exited before CDP became ready`);
      }
    }
  }

  throw new Error(`Timed out waiting for headless Chrome CDP on port ${args.cdpPort}`);
}

async function getCookieHeader(args) {
  const appHost = new URL(args.appUrl).host;
  const { targets, browserProcess } = await targetsWithOptionalLaunch(args);
  const target =
    targets.find((item) => item.type === "page" && String(item.url || "").includes(appHost)) ||
    targets.find((item) => item.type === "page");

  if (!target?.webSocketDebuggerUrl) {
    throw new Error(`No OpenClaw browser page target found for ${appHost}`);
  }

  try {
    const result = await callCdp(target.webSocketDebuggerUrl, "Network.getAllCookies");
    const now = Date.now() / 1000;
    const cookies = (result.cookies || [])
      .filter((cookie) => isCookieForHost(cookie, appHost))
      .filter((cookie) => !cookie.expires || cookie.expires > now)
      .sort((a, b) => String(a.name).localeCompare(String(b.name)));

    if (!cookies.length) {
      throw new Error(`No valid AI Music cookies found for ${appHost}; manual browser login is required`);
    }

    return cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; ");
  } finally {
    if (browserProcess) {
      browserProcess.kill("SIGTERM");
    }
  }
}

async function readTextIfExists(path) {
  try {
    const response = await import("node:fs/promises").then((fs) => fs.readFile(path, "utf8"));
    return response;
  } catch (error) {
    if (error?.code === "ENOENT") return "";
    throw error;
  }
}

async function updateEnvFile({ envFile, apiBase, cookieHeader }) {
  const previous = await readTextIfExists(envFile);
  const preserved = previous
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("AIMP_LOCAL_API_BASE=") && !line.startsWith("AIMP_API_COOKIE="));

  const next = [
    ...preserved,
    `AIMP_LOCAL_API_BASE=${apiBase}`,
    `AIMP_API_COOKIE=${shellQuote(cookieHeader)}`,
    "",
  ].join("\n");

  if (next === previous) return false;

  const timestamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+$/, "Z");
  if (previous) {
    await copyFile(envFile, `${envFile}.bak.${timestamp}`);
  }

  const tempPath = `${dirname(envFile)}/.${envFile.split("/").pop()}.${process.pid}.tmp`;
  await writeFile(tempPath, next, { encoding: "utf8", mode: 0o600 });
  await chmod(tempPath, 0o600);
  await rename(tempPath, envFile);
  return true;
}

function restartUserService(serviceName) {
  const result = spawnSync("systemctl", ["--user", "restart", serviceName], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (result.status !== 0) {
    throw new Error(`Failed to restart ${serviceName}: ${result.stderr || result.stdout}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cookieHeader = await getCookieHeader(args);
  const changed = await updateEnvFile({
    envFile: args.envFile,
    apiBase: args.apiBase,
    cookieHeader,
  });

  if (changed && args.restartService) {
    restartUserService(args.restartService);
  }

  console.log(
    JSON.stringify({
      ok: true,
      changed,
      env_file: args.envFile,
      api_base: args.apiBase,
      cookie_bytes: cookieHeader.length,
      restarted: Boolean(changed && args.restartService),
    }),
  );
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: error.message }));
  process.exit(1);
});
