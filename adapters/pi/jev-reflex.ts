import { Type } from '@earendil-works/pi-ai';
import { defineTool, type ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { callReflex } from './bridge.mjs';

export default function (pi: ExtensionAPI) {
  pi.registerTool(defineTool({
    name: 'jev_reflex',
    label: 'Jev Reflex',
    description: 'Bounded advisory decisions via the locally installed Jev Reflex CLI. Use status first, then explicit selected-text batches or recipes. No execution or completion authority. Preserve request_id on uncertain outcomes; never retry with a new ID. See the Jev Reflex skill for schemas.',
    parameters: Type.Object({
      method: Type.Union(['status','batch','recipe','context','record_outcome','metrics'].map(x => Type.Literal(x))),
      arguments: Type.Record(Type.String(), Type.Unknown()),
    }),
    async execute(_id, params, signal) {
      const result = await callReflex(params.method, params.arguments, { signal });
      return { content: [{ type: 'text', text: JSON.stringify(result) }], details: result };
    },
  }));
}
