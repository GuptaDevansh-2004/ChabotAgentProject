export const preprocessMarkdown = (text: string) => {
    const lines = text.split(/\r?\n/);
    const out: string[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      // preserve code blocks completely
      if (trimmed.startsWith('```')) {
        out.push(line);
        i++;
        while (i < lines.length) {
          out.push(lines[i]);
          if (lines[i].trim().startsWith('```')) { i++; break; }
          i++;
        }
        continue;
      }

      // preserve explicit empty lines (single blank line)
      if (trimmed === '') {
        // push exactly one blank line to separate blocks
        out.push('');
        i++;
        continue;
      }

      // preserve list blocks: unordered (-, *, +) or ordered (1.)
      if (/^\s*([-*+]\s+|\d+\.\s+)/.test(line)) {
        // accumulate contiguous list lines (allow intermediate blank lines inside list)
        while (i < lines.length && (lines[i].trim() === '' || /^\s*([-*+]\s+|\d+\.\s+)/.test(lines[i]))) {
          out.push(lines[i]);
          i++;
        }
        // ensure a blank line after the whole list block
        out.push('');
        continue;
      }

      // headings, hr (---), blockquotes: keep them and ensure separation
      if (/^#{1,6}\s+/.test(trimmed) || /^-{3,}\s*$/.test(trimmed) || /^>\s?/.test(trimmed)) {
        out.push(line);
        out.push('');
        i++;
        continue;
      }

      // default: treat this single non-list line as its own paragraph -> add blank line after it
      out.push(line);
      out.push('');
      i++;
    }

    // collapse any accidental multiple blank lines down to one blank line between blocks
    const result = out.join('\n').replace(/\n{3,}/g, '\n\n');

    // trim one trailing newline if present (optional)
    return result.replace(/\s+$/g, '');
  };