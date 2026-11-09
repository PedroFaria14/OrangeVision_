import { useMemo } from 'react';
import { Studio } from '@prisma/studio-core/ui';
import { createStudioBFFClient } from '@prisma/studio-core/data/bff';
import { createPostgresAdapter } from '@prisma/studio-core/data/postgres-core';
import { NuqsAdapter } from 'nuqs/adapters/react';

export default function StudioFrame() {
  const adapter = useMemo(
    () =>
      createPostgresAdapter({
        executor: createStudioBFFClient({ url: '/api/admin/studio' }),
      }),
    [],
  );
  return (
    <NuqsAdapter>
      <Studio adapter={adapter} />
    </NuqsAdapter>
  );
}
