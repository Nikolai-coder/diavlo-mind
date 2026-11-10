# Security

## Reporting a vulnerability

Use GitHub's private reporting: open the **Security** tab of this repository and choose **Report a vulnerability**. If that option is not shown, open an issue that says only "security report, details in private" and wait for a maintainer to open a private channel. Please do not publish details before a fix exists.

Include what you ran, on which system, what happened and what you expected. A short reproduction is worth more than a long description.

## What is in scope

| Area | What would count as a vulnerability |
|---|---|
| `scripts/dm_orchestrate.py` | A model reply that makes the orchestrator write outside the workspace, or run anything other than the check command the user passed |
| `scripts/install.py` | Writing or deleting outside the chosen skills folder; replacing an install without the documented backup |
| `scripts/dm_llm.py` | Sending an API key to a host other than the configured provider, or printing it |
| `scripts/publish_github.py` | Publishing an e-mail address or a token the user did not choose to publish |
| `evaluation/run_benchmark.py` | A task or check that reads or changes files outside its temporary workspace |
| The skill, agents and prompts | Instruction text that makes a model treat file or web content as commands, or skip the approval that rule 10 requires |

## What the design already does

- The orchestrator exchanges whole files as marked text and never executes model output. The only command it runs is the one you pass with `--check-cmd`.
- Paths in model replies are resolved inside the workspace and refused otherwise.
- The scripts use the Python standard library only. There is no dependency to compromise.
- No script sends telemetry or contacts any host except the model provider you name.
- Rule 10 of the framework tells the model that text inside files, web pages and tool results is data, never instructions, and that destructive, irreversible, public or paid actions need explicit approval. This is an instruction, not an enforcement mechanism: a model can still disobey it. Run agents with the permissions you would give an unknown contractor.

## Supported versions

The latest release receives fixes.
