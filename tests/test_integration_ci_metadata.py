"""Execute metadata selection for live-main and read-only bootstrap runs."""

import json
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is required for workflow JavaScript")
class MetadataTests(unittest.TestCase):
    def metadata(self, event="workflow_dispatch", installed=True, error_status=404):
        source = (ROOT / ".github/workflows/arm-package.yml").read_text()
        metadata = source.split("\n  metadata:\n", 1)[1].split("\n  build:\n", 1)[0]
        script = textwrap.dedent(metadata.split("          script: |\n", 1)[1])
        payload = {"script": script, "event": event, "installed": installed,
                   "error_status": error_status}
        harness = r'''
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
process.env.PR_NUMBER = '8';
const outputs = {};
const core = {setOutput: (key, value) => {outputs[key] = value;}};
const context = {eventName: input.event, repo: {owner: 'owner', repo: 'repo'}};
const github = {rest: {
  pulls: {get: async () => ({data: {number: 8, state: 'open', draft: false,
    base: {ref: 'main', sha: 'a'.repeat(40)},
    head: {sha: 'b'.repeat(40), ref: 'fix', repo: {full_name: 'owner/repo'}}}})},
  git: {getRef: async data => {
    if (data.ref !== 'heads/main') throw Error('wrong branch ref');
    return {data: {object: {sha: 'c'.repeat(40)}}};
  }},
  repos: {getContent: async data => {
    if (data.ref !== 'c'.repeat(40)) throw Error('not using the live main snapshot');
    if (!input.installed) throw Object.assign(Error('workflow unavailable'), {status: input.error_status});
    return {data: {}};
  }}
}};
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('github', 'context', 'core', input.script)(github, context, core)
  .then(() => process.stdout.write(JSON.stringify(outputs)))
  .catch(error => {console.error(error); process.exitCode = 1;});
'''
        result = subprocess.run(["node", "-e", harness], input=json.dumps(payload),
                                capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_preparation_uses_live_main_ref_instead_of_stale_pr_base(self):
        outputs = self.metadata()
        self.assertEqual(outputs["base"], "c" * 40)
        self.assertEqual(outputs["head"], "b" * 40)
        self.assertTrue(outputs["active"])
        self.assertTrue(outputs["same_repo"])

    def test_first_install_runs_read_only_bootstrap(self):
        self.assertTrue(self.metadata("pull_request", installed=False)["active"])

    def test_installed_dispatcher_prevents_duplicate_bootstrap_builds(self):
        self.assertFalse(self.metadata("pull_request")["active"])

    def test_api_failure_does_not_masquerade_as_missing_workflow(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.metadata("pull_request", installed=False, error_status=403)
