---
name: skill-writing
description: Write project-specific skill files for the later agents, based on the spec you just wrote
---

# Skill Writing Skill

You are still the PM Agent. You just wrote the spec for this app, so you know what kind of app it is and where a generic developer would get it wrong.

Every later agent is given a skill file: its instructions. By default every app gets the same fixed skill files, so nothing in them is specific to what is being built. Your job now is to write a version of each one that fits THIS app.

## What to do

For each stage listed under "Files to write" at the end of these instructions:

1. Read the base skill file.
2. Write the project-specific version to the target path.

## Rules

- Keep everything in the base file that is about process and output format: the section headings the agent must write, the memory file rules, the git workflow, the required formats. Other code depends on these.
- Keep the YAML front matter (`name`, `description`) unchanged.
- Add a section `## Rules for this project` with 5 to 10 concrete rules that follow from the spec. A good rule names a specific thing in this app.
- Remove or rewrite base rules and examples that do not apply to this app.
- Do not weaken any rule about security, error handling, or the build passing.
- Write only the files listed. Code review and security review always use their fixed skill files, so do not write versions of those.

## What a good project rule looks like

- Quiz app: "Keep every question in one data file, `src/data/questions.ts`. Never hardcode a question inside a component."
- Chat app: "A new message must appear without a page refresh: subscribe to Supabase realtime on the messages table."
- Store app: "Never trust a price sent from the browser. Look the price up in the database on the server."

A bad rule is one that would be true of any app ("write clean code", "handle errors").

## Output

After writing the files, reply with a short summary only, in this format:

### Project rules

- **architecture**: the rules you added, one line each
- **coding**: ...
- **test-writing**: ...
- **deploy-checklist**: ...
