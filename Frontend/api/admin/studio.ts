import { handleAdminStudio } from '../../server/admin/studio.js';

export default {
  fetch(request: Request): Promise<Response> {
    return handleAdminStudio(request);
  },
};
