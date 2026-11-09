import { handleAdminAuth } from '../../server/admin/auth.js';

export default {
  fetch(request: Request): Promise<Response> {
    return handleAdminAuth(request);
  },
};
