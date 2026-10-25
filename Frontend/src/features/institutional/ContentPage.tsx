import { Page } from '@/shared/ui/Page';
import { contents, type ContentSlug } from './content';

export default function ContentPage({ slug }: { slug: ContentSlug }) {
  const content = contents[slug];
  return (
    <Page title={content.title} description={content.description}>
      {content.sections.map(([title, text]) => (
        <section key={title}>
          <h2>{title}</h2>
          <p>{text}</p>
        </section>
      ))}
      {slug === 'referencias' && (
        <ul>
          {[
            ['OpenCV', 'https://docs.opencv.org/4.x/'],
            ['Raspberry Pi', 'https://www.raspberrypi.com/documentation/'],
            ['Python', 'https://docs.python.org/3/'],
            ['SQLite', 'https://www.sqlite.org/docs.html'],
            ['PostgreSQL', 'https://www.postgresql.org/docs/'],
            ['FastAPI', 'https://fastapi.tiangolo.com/'],
            ['React', 'https://react.dev/learn'],
          ].map(([label, url]) => (
            <li key={url}>
              <a href={url}>{label} — documentação oficial</a>
            </li>
          ))}
        </ul>
      )}
      <aside>
        <p>{content.pending}</p>
      </aside>
    </Page>
  );
}
