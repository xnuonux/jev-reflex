import { spawn } from 'node:child_process';
import { StringDecoder } from 'node:string_decoder';

const METHODS = new Set(['status', 'batch', 'shared', 'bulk', 'inspect_job', 'cancel_job','controller_open','controller_event','controller_inspect','workflow','host_event','artifact_put','artifact_get','calibration_audit', 'recipe', 'context', 'record_outcome', 'metrics']);

// Host-owned command configuration only. Never take command/args from a model tool argument.
export async function callReflex(method, args, { command = 'jev-reflex', prefixArgs = [], signal, timeoutMs = 60000 } = {}) {
  if (!METHODS.has(method) || !args || typeof args !== 'object' || Array.isArray(args)) throw new Error('jev-reflex:arguments');
  const wire = JSON.stringify(args);
  if (Buffer.byteLength(wire) > 16777216) throw new Error('jev-reflex:arguments-size');
  if (signal?.aborted) throw new Error('jev-reflex:cancelled-before-dispatch');
  return new Promise((resolve, reject) => {
    const child = spawn(command, [...prefixArgs, 'call', method], { shell: false, windowsHide: true, stdio: ['pipe','pipe','pipe'] });
    let done = false, output = '', bytes = 0;
    const decoder = new StringDecoder('utf8');
    const finish = (error, value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
      if (error) { child.kill(); reject(new Error(error)); } else resolve(value);
    };
    const abort = () => finish('jev-reflex:cancelled-outcome-unknown-do-not-retry');
    const timer = setTimeout(() => finish('jev-reflex:timeout-outcome-unknown-do-not-retry'), timeoutMs);
    signal?.addEventListener('abort', abort, { once: true });
    child.on('error', () => finish('jev-reflex:launch-failed'));
    child.stdin.on('error', () => {});
    child.stderr.resume(); // Never echo subprocess/provider prose or credentials.
    child.stdout.on('data', chunk => {
      bytes += chunk.length;
      if (bytes > 16777216) return finish('jev-reflex:response-size');
      output += decoder.write(chunk);
    });
    child.on('close', code => {
      output += decoder.end();
      if (code !== 0) return finish('jev-reflex:call-failed');
      try {
        const value = JSON.parse(output);
        if (typeof value?.status !== 'string' || value.authority !== 'none' || value.may_execute !== false) return finish('jev-reflex:invalid-envelope');
        finish(null, value);
      } catch { finish('jev-reflex:invalid-json'); }
    });
    child.stdin.end(wire);
  });
}
