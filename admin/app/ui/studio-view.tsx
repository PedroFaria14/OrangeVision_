'use client';

import { useMemo } from 'react';
import { Studio } from '@prisma/studio-core/ui';
import { createStudioBFFClient } from '@prisma/studio-core/data/bff';
import { createPostgresAdapter } from '@prisma/studio-core/data/postgres-core';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

export default function StudioView() {
  const adapter = useMemo(() => createPostgresAdapter({
    executor: createStudioBFFClient({ url: '/api/studio' }),
  }), []);
  return <NuqsAdapter><Studio adapter={adapter} /></NuqsAdapter>;
}
