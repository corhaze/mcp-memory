import { marked } from 'marked';

export default function MarkdownBody({ content, className = '' }) {
  if (!content) return null;

  const html = marked.parse(content);
  const classes = ['markdown-body', className].filter(Boolean).join(' ');

  return (
    <div
      className={classes}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
