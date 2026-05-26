// 知乎 API 调用封装

const ZhihuAPI = {
    baseUrl: '/api',

    // 获取知乎回答列表
    async getAnswers(params = {}) {
        const query = new URLSearchParams();
        if (params.creator) query.append('creator', params.creator);
        if (params.search) query.append('search', params.search);
        if (params.offset) query.append('offset', params.offset);
        if (params.limit) query.append('limit', params.limit);

        const response = await fetch(`${this.baseUrl}/zhihu?${query}`);
        if (!response.ok) throw new Error('Failed to fetch zhihu answers');
        return response.json();
    },

    // 获取知乎统计
    async getStats() {
        const response = await fetch(`${this.baseUrl}/zhihu/stats`);
        if (!response.ok) throw new Error('Failed to fetch zhihu stats');
        return response.json();
    },

    // 获取知乎回答详情
    async getAnswerDetail(contentId) {
        const response = await fetch(`${this.baseUrl}/zhihu/${contentId}`);
        if (!response.ok) throw new Error('Failed to fetch answer detail');
        return response.json();
    },

    // 获取创作者列表
    async getCreators() {
        const response = await fetch(`${this.baseUrl}/zhihu/creators`);
        if (!response.ok) throw new Error('Failed to fetch creators');
        return response.json();
    }
};
