import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BLOG_ORIGIN = 'https://iamjaehka13.blog';
const SEARCH_URL = `${BLOG_ORIGIN}/assets/js/data/search.json`;
const LIST_PAGES = [`${BLOG_ORIGIN}/`, `${BLOG_ORIGIN}/page2/`, `${BLOG_ORIGIN}/page3/`];
const OUTPUT_PATH = path.join(process.cwd(), 'src/data/study-posts.json');

const fetchText = async (url) => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }

  return response.text();
};

const stripTags = (html) =>
  html
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const decodeEntities = (text) =>
  text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ');

const slugFromUrl = (url) => url.split('/').filter(Boolean).at(-1);

const absoluteBlogUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url.replace('https://iamjaehka13.github.io', BLOG_ORIGIN);
  return new URL(url, BLOG_ORIGIN).href;
};

const parseListPage = (html) => {
  const previews = new Map();
  const articlePattern = /<article class="card-wrapper card">([\s\S]*?)<\/article>/g;
  let match;

  while ((match = articlePattern.exec(html))) {
    const block = match[1];
    const href = block.match(/<a href="([^"]+)"/)?.[1];

    if (!href) {
      continue;
    }

    previews.set(href, {
      image: absoluteBlogUrl(block.match(/<img src="([^"]+)"/)?.[1] ?? ''),
      summary: decodeEntities(
        stripTags(block.match(/<div class="card-text content mt-0 mb-3">([\s\S]*?)<\/div>/)?.[1] ?? ''),
      ),
    });
  }

  return previews;
};

const extractPostContent = (html, slug) => {
  const content = html.match(/<div class="content">([\s\S]*?)<div class="post-tail-wrapper/)?.[1] ?? '';

  return content
    .replace(/<a href="#[^"]+" class="anchor[^>]*>[\s\S]*?<\/a>/g, '')
    .replace(/\sid="([^"]+)"/g, ` id="${slug}-$1"`)
    .replace(/\shref="#([^"]+)"/g, ` href="#${slug}-$1"`)
    .replace(/(src|href)="\/(assets\/[^"]+)"/g, `$1="${BLOG_ORIGIN}/$2"`)
    .replace(/href="\/(posts\/[^"]+)"/g, `href="${BLOG_ORIGIN}/$1"`);
};

const main = async () => {
  const [searchJson, ...listHtml] = await Promise.all([
    fetchText(SEARCH_URL),
    ...LIST_PAGES.map(fetchText),
  ]);

  const previewMap = listHtml.reduce((map, html) => {
    parseListPage(html).forEach((value, key) => map.set(key, value));
    return map;
  }, new Map());

  const sourcePosts = JSON.parse(searchJson);
  const posts = [];

  for (const sourcePost of sourcePosts) {
    const slug = slugFromUrl(sourcePost.url);
    const sourceUrl = absoluteBlogUrl(sourcePost.url);
    const postHtml = await fetchText(sourceUrl);
    const preview = previewMap.get(sourcePost.url) ?? {};

    posts.push({
      slug,
      title: sourcePost.title,
      date: sourcePost.date.slice(0, 10),
      categories: sourcePost.categories.split(',').map((category) => category.trim()),
      tags: sourcePost.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      summary: preview.summary || sourcePost.content.slice(0, 160),
      image: preview.image || '',
      sourceUrl,
      contentHtml: extractPostContent(postHtml, slug),
    });
  }

  const output = {
    source: BLOG_ORIGIN,
    license: 'CC BY 4.0',
    crawledAt: new Date().toISOString(),
    posts,
  };

  await mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await writeFile(OUTPUT_PATH, `${JSON.stringify(output, null, 2)}\n`);
  console.log(`Wrote ${posts.length} posts to ${OUTPUT_PATH}`);
};

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
