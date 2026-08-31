---
name: elementary-math
description: Design elementary mathematics lessons, worksheets, and print-quality Chinese PDF materials using first-principles explanations, age-appropriate visual models, guided discovery, local checks after every concept, and comprehensive assessments. Use when teaching primary-school math, creating visual math exercises, explaining arithmetic laws conceptually, or producing Chinese LaTeX worksheets and answer keys.
---

# Elementary Mathematics

Create materials that help children understand why mathematics works before asking them to memorize rules.

## Teaching principles

1. Start from concrete actions or invariant relationships, not a formula.
2. Move through this sequence:
   - concrete situation or action;
   - visual model;
   - spoken explanation;
   - numerical examples;
   - symbolic generalization;
   - application.
3. Ask children to observe, compare, predict, draw, and explain.
4. Introduce formal terminology only after examples reveal the pattern.
5. Keep numbers and language appropriate for the intended grade.
6. Distinguish a calculation result from the reason it is valid.

## Required lesson structure

Before writing, list the knowledge points the material must teach. Use this structure:

1. Begin with a short concrete situation that reveals the first idea.
2. For every knowledge point, in order:
   - show an explanatory visual model first, and let the visual carry the concept before any rule is stated;
   - guide the learner to observe what changes and what stays invariant;
   - explain the idea in spoken language;
   - connect the picture to numerical examples and then symbols;
   - immediately give 1--3 exercises that check understanding of this concept (not yet comprehensive application).
3. Do not postpone all exercises until the end. A learner must practice each idea before the next idea is introduced.
4. End with exactly 5 comprehensive problems that jointly cover every knowledge point in the material. Include at least one multi-step problem and one explanation or error-diagnosis problem.
5. Keep student pages and the answer key separate. In the answer key, explain the reasoning for visual, conceptual, and comprehensive problems.

Before delivery, check that every listed knowledge point maps to:

- at least one meaningful visual explanation;
- 1--3 local exercises that check understanding of the concept;
- at least one local or comprehensive answer with reasoning;
- at least one item in the final 5-problem comprehensive assessment.

## Visual models

Choose the model that exposes the mathematical structure:

- number line: addition/subtraction as directed movement and distance;
- counters or ten-frames: composition, decomposition, and place value;
- bar model: part-whole and comparison relationships;
- array or area model: multiplication, division, and distributivity;
- geometric transformation: symmetry, congruence, and spatial reasoning.

The diagram must carry explanatory meaning. Label the start, action, quantity, and result when relevant. Do not add decorative graphics that compete with the mathematics.

Every knowledge point must have a visual model unless the user explicitly requests text-only material. A visual must make the inference visible, not merely illustrate the story:

- draw every counted object, unit square, segment, or group needed for the argument;
- label quantities, groups, boundaries, and the operation represented;
- use consistent colors for equal quantities and contrasting colors for parts with different roles;
- place related diagrams together so the learner can compare them;
- state in words what changed and what remained unchanged;
- connect each visible part directly to a term in the expression.

Use only units and terminology already available to the learner. If the grade or prior knowledge is unknown, prefer counters, grids, "格", "份", and "单位正方形" over centimetres, square centimetres, or other formal measurement units.

## Drawing number lines with TikZ

Number lines are the most error-prone diagram. Apply these rules, learned from repeated overlap fixes:

### Axis style and ticks

Define one reusable `axis` style and one `tick` style so every line looks consistent:

```latex
\usetikzlibrary{decorations.pathreplacing,arrows.meta}
\tikzset{
  axis/.style={thick,black,-{Latex[length=2mm]}},
  tick/.style={black,thick},
  pt/.style={coreblue},          % point/dot colour
  concorange/.style={...},      % contrast colour
  linegray/.style={gray},
}
```

Note: the arrow spec is `{Latex[length=2mm]}-{Latex[length=2mm]}` for a double-headed axis. Writing `{-Latex}-` triggers "Unknown arrow tip kind '-Latex'".

### Label every tick below the axis

For primary-school readers, label **every** tick with its number directly below the axis, not just the endpoints. Place tick labels one row below the line:

```latex
\draw[axis] (-0.4,0) -- (6.4,0);
\foreach \x in {0,1,2,3,4,5,6} {\draw[tick] (\x,-0.15)--(\x,0.15);}
\node[below,linegray,font=\small] at (0,-0.2) {$0$};
\node[below,linegray,font=\small] at (1,-0.2) {$\tfrac{1}{6}$};
...
```

### Keep all point labels BELOW the axis

The single most common overlap bug is putting point labels (`\node[above,...] at (x,0.15)`) above the axis, where they collide with the preceding paragraph or a figure stacked above. **Default to placing point labels below the axis**, as a second row under the tick labels:

```latex
\fill[pt] (3,0) circle (2.2pt);
\node[below,coreblue,font=\normalsize] at (3,-0.75) {$\tfrac{1}{2}$};
```

Only put a label above the axis when there is genuinely nothing above the figure on the page.

### Comparing fractions: use separate aligned axes, not one stacked axis

When showing that several fractions are equal (e.g. \(1/2 = 2/4 = 4/8\)) or equivalent under 约分/通分, **draw one number line per fraction**, stacked vertically and aligned at 0 and 1, rather than cramming all fractions onto a single axis. Stacking labels for multiple fractions at the same axis point makes them overlap and become unreadable.

Each axis gets its own scale (e.g. halves, quarters, eighths), its own coloured dot at the fraction's position, and a coloured below-axis label. Vertical dashed arrows between axes show the transformation (`\div 2 →`). Keep the 0 and 1 of every axis on the same vertical lines so the learner can read equality by eye.

### Spacing and page-break safety

- Put `\vspace` (or `\vspace*` before a potential page break) around every `tikzpicture` so the figure never touches the surrounding text. 10–14pt above and below is usually enough; increase when a figure has below-axis point labels or braces.
- When a figure has both a caption and a brace below the axis, separate them onto different rows: tick labels at `y=-0.2`, point labels at `y=-0.75`, brace at `y=-0.85`, brace label at `y=-1.1`. Stacking them too close causes overlap.
- Prefer moving captions **outside** the `tikzpicture` (as `\centerline{\small ...}` immediately after `\end{center}`) instead of internal TikZ `\node` text. External captions flow with the page and are easier to space.
- If one combined `tikzpicture` keeps colliding with text, split it into multiple `tikzpicture` environments, each with its own `\vspace`.
- Use `\nopagebreak` or keep a figure with its introducing sentence when a figure and its caption would otherwise split across pages.

### Braces for "how much difference"

Use `decorations.pathreplacing` with a mirrored brace to mark the gap between two points, and place the brace label one row below the brace:

```latex
\draw[decorate,decoration={brace,amplitude=4pt,mirror},linegray] (2,-0.85)--(3,-0.85);
\node[below,linegray,font=\small] at (2.5,-1.1) {差 $\tfrac{1}{6}$};
```

## Multiplication and divisibility visual patterns

When these topics appear, use the following defaults.

### Meanings of multiplication

- Repeated addition: show equal groups or a complete array, then match every group to one addend.
- Efficient counting: show how rows and columns replace counting objects one by one.
- Area: draw the full rectangle and every unit square inside it. Label rows and columns and count area as the number of unit squares. Do not show only corner marks, dots, or an empty rectangle.
- Multiplier roles: choose and state one convention such as "每份数量 × 份数". Explain that swapping factors preserves the product but changes their contextual roles.

### Laws of multiplication

- Commutativity: rotate or reinterpret the same complete array. Show that rows and columns exchange while no object is added or removed.
- Associativity: use the same rectangle of unit squares and count it in two grouping orders. For example, in a \(2\)-row, \(12\)-column rectangle, group the columns into four \(3\)-column blocks:
  \[
  (2\times3)\times4=2\times(3\times4).
  \]
  Label both readings on the picture. Do not rely only on nested boxes or a verbal packaging story.
- Distributivity: split one complete rectangle along a grid line, keep every unit square visible, and match each sub-rectangle to one product:
  \[
  (a+b)\times c=a\times c+b\times c.
  \]
- For every law, include a non-example or incorrect transformation and ask the learner to diagnose it.

### Multiplicative comparison

Use aligned bar models or rows of equal squares to compare:

- the original one part;
- "\(A\) is \(k\) times \(B\)": \(k\) total equal parts;
- "\(A\) is \(k\) times more than \(B\)": the original one part plus \(k\) additional equal parts, for \(k+1\) total parts.

Place the models together, color the original part consistently, color added parts differently, and label "原来的1份" and "多出的\(k\)份". Explicitly contrast "\(k\)倍", "多\(k\)倍", and "多\(k\)".

### Factors, common factors, and multiples

- Factors and factorization: arrange all objects into rectangles and read factor pairs from row and column counts; use a factor tree only after factor pairs are understood.
- Common factors and greatest common factor: show two quantities partitioned into equal groups and compare all valid common group sizes before selecting the greatest.
- Common multiples and least common multiple: align skip-counting tracks, number lines, schedules, or ordered multiple lists; mark coincidences and identify the first positive coincidence.
- Keep "largest equal grouping" visually distinct from "first shared recurrence" so greatest common factor and least common multiple are not confused.

## Guided-discovery pattern

When introducing a law or property:

1. Show at least two small examples.
2. Represent both sides with the same visual model.
3. Ask what changed and what stayed invariant.
4. Let the learner state the pattern in words.
5. Present the symbolic form.
6. Include a non-example or common misconception.
7. Apply the property in a purposeful calculation.

For addition:

- Interpret \(a+b\) as starting at \(a\) and moving \(b\) units right on a number line.
- Derive \(a+b=b+a\) by comparing two routes with the same total lengths in opposite order.
- Derive \((a+b)+c=a+(b+c)\) by regrouping the same three consecutive lengths.
- Explicitly distinguish changing order from changing grouping.
- Explain \(a+0=a\) as a movement of zero units.

## Exercise design

Build a progression rather than a list of near-duplicate calculations:

1. read or complete a visual example;
2. draw the model from a given expression;
3. write an expression from a model or story;
4. fill a missing value;
5. compare two representations without calculating;
6. explain why a statement is true;
7. diagnose an incorrect argument;
8. apply the idea to simplify a calculation;
9. solve an open-ended task with multiple valid answers.

Use enough blank space for drawing and written reasoning. Provide answers and short reasoning for conceptual questions. Keep the answer key separate from student pages when practical.

Immediately after each knowledge-point explanation, include a short local check of 1--3 questions that progress through at least two of these forms:

1. read or complete the model just shown;
2. draw the model from an expression or story;
3. write an expression from a model;
4. fill a missing value or label;
5. compare two representations without calculating;
6. explain why a statement is true;
7. diagnose an incorrect argument;
8. apply the idea in a new context.

Avoid sets made only of near-duplicate calculations. At least one local exercise must require a drawing or explanation. Keep the local check focused on concept understanding; reserve combined or multi-step application for the final comprehensive assessment.

## Comprehensive assessment

End the student section with a clearly titled comprehensive assessment of exactly 5 problems that:

- together cover every knowledge point introduced in the material;
- combine two or more ideas in at least one problem;
- include representation, calculation, explanation, and transfer;
- include at least one multi-step problem and one explanation or error-diagnosis problem;
- avoid introducing new units, notation, or contexts that were not taught;
- provide enough space for diagrams and reasoning;
- give complete answers and short justifications in the separate answer key.

Before finalizing, make a private coverage map from each of the 5 comprehensive problems to the knowledge points it tests. Add or revise problems until no knowledge point is omitted.

## Simplifying calculations

Teach "friendly numbers" as a consequence of the laws, not as an unexplained trick:

1. identify a pair that forms a convenient total such as \(10\) or \(100\);
2. use commutativity to place the pair together if needed;
3. use associativity to calculate that pair first;
4. annotate which law justifies each transformation.

Do not accept a correct total paired with an invalid transformation.

## Chinese print-quality PDF workflow

Use XeLaTeX with `ctexart`, `amsmath`, and TikZ for editable vector diagrams.

Default typography:

- A4 page with compact but readable margins;
- do not create a standalone cover unless the user explicitly requests one; place a compact title and name/date fields above the first lesson;
- omit page headers by default; a small page number in the footer is sufficient;
- let sections flow continuously and do not force a new page between chapters;
- minimize unused vertical space while preserving room that students actually need for drawing and written answers;
- body text in regular Kaiti, without bold emphasis;
- reserve bold sans-serif for the title, section headings, and box headings;
- use LaTeX math mode for all mathematical symbols and formulas;
- use restrained, high-contrast colors that remain readable when printed;
- avoid splitting an example, diagram, or conclusion across pages.

Locate an installed Kaiti font instead of assuming a font name resolves in every environment. Prefer an explicit font file path when compilation is sandboxed. Keep Latin and mathematics fonts separate from the CJK body font.

### Font size control (XeLaTeX + ctex)

`ctexart` (based on `article`) silently ignores arbitrary class options such as `14pt`, `16pt` — it only honours the standard `10/11/12pt` sizes. When the user asks for a larger body size (common for primary-school materials), switch the document class to `extarticle`, which supports any of `8pt…20pt`, and load ctex as a package for CJK only:

```latex
\documentclass[14pt,a4paper]{extarticle}
\usepackage[fontset=none,scheme=plain]{ctex}
```

`fontset=none` disables ctex's bundled font sets so your explicit `\setCJKmainfont` calls take effect; `scheme=plain` keeps the layout plain (no fancy headings). Verify the size actually changed by checking the page count — a real 14pt switch typically adds 1–2 pages versus 11pt.

### Loading Kaiti reliably on macOS

`fontspec` often cannot resolve system Kaiti by family name (`STKaiti`, `Kaiti`) because the files live in dynamic asset paths under `/System/Library/AssetsV2/...`. Two robust approaches:

1. Find the real file with `fc-list :lang=zh family file | rg -i kai`, then point `\setCJKmainfont` at an explicit `Path=` with the file copied into the project folder:
   ```latex
   \setCJKmainfont[Path=./,AutoFakeBold=2.5,FaceIndex=0]{Kaiti.ttc}
   ```
   `AutoFakeBold` synthesises a bold weight (Kaiti has none natively); `FaceIndex=0` picks the first face of a `.ttc` collection.
2. Or fall back to a stable system family name such as `Songti SC` / `Heiti SC`, which `fontspec` resolves reliably.

Always confirm the chosen font exists before compiling; do not assume a font name resolves in every environment.

### Output file location: use the user-level temp directory

Place all generated deliverables and build artifacts in the user-level temporary directory, not in the workspace. On macOS this is `$TMPDIR` (typically `/var/folders/.../T/`); on Linux use `$TMPDIR` falling back to `/tmp`. Keeping output out of the workspace avoids polluting the source tree with large binary artifacts (PDFs, font files, aux logs).

Conventions:

- create one subfolder per material: `$TMPDIR/<material-name>/` (e.g. `$TMPDIR/fractions-lesson/`);
- compile into that folder: `xelatex -output-directory="$TMPDIR/<material-name>" <src>.tex`;
- copy the final deliverables there: the `.pdf`, the editable `.tex` source, and any font file the `.tex` references by relative path (e.g. `Kaiti.ttc`) so the source still compiles standalone from that folder;
- do not leave `build/`, `.aux`, `.log`, preview PNGs, or font copies inside the workspace — those are intermediate and belong only in the temp directory;
- report the absolute temp path to the user, since `$TMPDIR` is per-user and per-session and is periodically cleared by the OS.

Note: writing outside the workspace usually requires lifting the sandbox (request `all` permissions for the copy/compile command). If the environment forbids that, fall back to a workspace-local `build/` directory and clearly tell the user it is intermediate output, not a deliverable location.

Use semantic visual hierarchy:

- blue or neutral boxes for core ideas;
- green boxes for observations;
- orange boxes for formal conclusions;
- consistent colors for the same movement or quantity across related diagrams.

## Required validation

Before delivering a PDF:

1. compile with XeLaTeX twice so page references stabilize;
2. check for compilation errors, missing glyphs, and overfull boxes;
3. render pages to images and visually inspect:
   - Chinese font and weight;
   - diagram labels and arrows;
   - clipping and overlap;
   - page breaks;
   - answer space;
   - page count and footer references;
4. revise and rebuild until the visual checks pass;
5. place the final PDF, the `.tex` source, and any referenced font files in the workspace; remove intermediate previews and aux files from both the temp folder and the workspace;
6. deliver the absolute temp path to the user, and keep both the PDF and editable `.tex` source unless the user requests otherwise.

## Quality checklist

- [ ] The concept begins with meaning, not a memorized procedure.
- [ ] Every knowledge point has a meaningful, fully labeled visual model.
- [ ] Every diagram supports a specific inference.
- [ ] Examples lead naturally to the symbolic statement.
- [ ] Rules are accompanied by a reason or invariant.
- [ ] Every knowledge point is followed immediately by 1--3 exercises that check concept understanding.
- [ ] Exercises progress from representation to explanation and transfer.
- [ ] Common misconceptions are addressed.
- [ ] The final comprehensive assessment has exactly 5 problems and covers every knowledge point.
- [ ] There is no unrequested cover, page header, or forced chapter break wasting paper.
- [ ] Body text is regular Kaiti and not bold.
- [ ] The requested body font size actually took effect (page count shifted vs. 11pt baseline); `ctexart` was replaced with `extarticle` if a non-standard size was requested.
- [ ] Number-line diagrams have all point labels below the axis; no above-axis label collides with preceding text.
- [ ] Fraction-comparison diagrams use separate 0-aligned axes (one per fraction), not labels stacked on a single axis.
- [ ] Mathematical notation is typeset consistently.
- [ ] Final PDF, `.tex` source, and referenced font files are placed in `$TMPDIR/<material-name>/`; no `build/`, aux, or preview files are left in the workspace.
- [ ] The PDF has been compiled and visually inspected.
