/*
 * OpenData.js
 * 取代原本內嵌於 HighValue.aspx / open.aspx 的 Vue 'open-data' 元件寫法。
 * 目的：移除執行期樣板編譯（Vue template 字串編譯需要 CSP unsafe-eval），
 * 改用原生 <template> DOM clone + jQuery 操作，並以 $.ajax 取代 axios。
 *
 * 使用方式（於頁面內）：
 *   OpenData.init('#app', {
 *       categoriesAction: '...',
 *       listsAction: '...',
 *       collectAction: '...',   // 選填
 *       pageUrl: '...',         // 選填
 *       loginUrl: '...',        // 選填
 *       initialOrd: 0,          // 選填，預設 0
 *       categoryDefs: [ { title, dataKey, paramKey, showMoreButton } ... ],
 *       renderResultItem: function (item) { return $(...); }
 *   });
 */
(function ($, window) {
    'use strict';

    function safeText($el, val) {
        $el.text(val === null || val === undefined ? '' : val);
    }

    function init(rootSelector, options) {
        var $root = $(rootSelector);
        if ($root.length === 0) {
            return null;
        }

        options = options || {};
        var categoryDefs = options.categoryDefs || [];

        var state = {
            isLoading: false,
            cateIndex: null,
            totalPage: 0,
            totalCount: 0,
            activeBtns: [],
            categories: [],
            filter: {
                page: 1,
                limit: 5,
                keyword: '',
                ord: options.initialOrd || 0
            },
            page: 0,
            prevKeyword: '',
            keywordTimer: null,
            lists: []
        };

        var $loading = $root.find('[data-role="loading"]');
        var $catTabs = $root.find('[data-role="category-tabs"]');
        var $catNavs = $root.find('[data-role="category-navs"]');
        var $keywordInput = $root.find('[data-role="keyword-input"]');
        var $filterList = $root.find('[data-role="filter-list"]');
        var $searchResult = $root.find('[data-role="search-result"]');
        var $currentPageText = $root.find('[data-role="current-page-text"]');
        var $sumText = $root.find('[data-role="sum-text"]');
        var $limitSelect = $root.find('[data-role="limit-select"]');
        var $gotoPageInput = $root.find('[data-role="goto-page-input"]');
        var $prevBtn = $root.find('[data-role="prev"]');
        var $nextBtn = $root.find('[data-role="next"]');
        var $messageModal = $root.find('[data-role="message-modal"]');
        var $messageText = $messageModal.find('[data-role="message-text"]');
        var $messageLoginLink = $messageModal.find('[data-role="message-login-link"]');

        function setLoading(isLoading) {
            state.isLoading = isLoading;
            $loading.toggle(!!isLoading);
        }

        function showMessage(msg) {
            if (msg) {
                safeText($messageText, msg);
                if (options.loginUrl) {
                    $messageLoginLink.attr('href', options.loginUrl);
                }
                $messageModal.addClass('is-active');
            } else {
                $messageModal.removeClass('is-active');
            }
        }

        $messageModal.on('click', '[data-role="message-close"], .modal-background, .modal-close', function () {
            showMessage('');
        });

        function renderCategoryNav() {
            if ($catTabs.length === 0 && $catNavs.length === 0) {
                return;
            }
            $catTabs.empty();
            $catNavs.empty();

            state.categories.forEach(function (category, index) {
                var $tab = $('<div class="category-current"></div>')
                    .attr('data-name', category.title)
                    .toggleClass('active', index === state.cateIndex)
                    .text(category.title)
                    .on('click', function () { toggleCateList(index); });
                $catTabs.append($tab);

                var $nav = $('<div class="category-nav"></div>');
                $('<div class="category-title"></div>').text(category.title).appendTo($nav);
                var $list = $('<div class="category-list"></div>').toggleClass('is-opened', index === state.cateIndex);
                var $btnWrapper = $('<ul class="category-btn-wrapper"></ul>');
                (category.btns || []).forEach(function (btn, btnI) {
                    var isActive = state.activeBtns[index] && state.activeBtns[index].index === btnI;
                    $('<li class="category-btn"></li>')
                        .attr('data-num', btn.Num)
                        .toggleClass('active', !!isActive)
                        .text(btn.Title)
                        .on('click', function () { filterCategory(index, btn, btnI); })
                        .appendTo($btnWrapper);
                });
                $list.append($btnWrapper);
                $nav.append($list);

                var def = categoryDefs[index];
                if (!def || def.showMoreButton !== false) {
                    $('<button type="button" class="category-more"></button>')
                        .on('click', function () { toggleCateList(index); })
                        .appendTo($nav);
                }
                $catNavs.append($nav);
            });
        }

        function renderFilterList() {
            $filterList.empty();
            state.activeBtns.forEach(function (activeBtn) {
                if (!activeBtn || !activeBtn.btn) {
                    return;
                }
                var $li = $('<li></li>').text(activeBtn.btn.Title);
                $('<i class="fas fa-times"></i>').on('click', function () {
                    activeBtn.index = null;
                    activeBtn.btn = null;
                    renderCategoryNav();
                    renderFilterList();
                    getLists();
                }).appendTo($li);
                $filterList.append($li);
            });
        }

        function renderResults() {
            $searchResult.empty();
            state.lists.forEach(function (item) {
                if (typeof options.renderResultItem === 'function') {
                    $searchResult.append(options.renderResultItem(item));
                }
            });
        }

        function renderPagination() {
            $currentPageText.text('第 ' + state.page + ' 頁 / 共 ' + state.totalPage + ' 頁');
            $sumText.text('共 ' + state.totalCount + ' 筆資料，每頁顯示');
            $prevBtn.toggleClass('disabled', (state.filter.page - 1) < 1);
            $nextBtn.toggleClass('disabled', (state.filter.page + 1) > state.totalPage);
            $limitSelect.val(state.filter.limit);
            $gotoPageInput.val(state.filter.page);
        }

        function render() {
            renderCategoryNav();
            renderFilterList();
            renderResults();
            renderPagination();
        }

        function toggleCateList(index) {
            state.cateIndex = (index === state.cateIndex) ? null : index;
            renderCategoryNav();
        }

        function filterCategory(index, btn, btnI) {
            var active = state.activeBtns[index];
            if (active && active.btn && active.btn.ID === btn.ID) {
                active.index = null;
                active.btn = null;
            } else {
                active.index = btnI;
                active.btn = btn;
            }
            renderCategoryNav();
            renderFilterList();
            getLists();
        }

        function goPage(page) {
            if (page < 1 || page > state.totalPage) {
                return;
            }
            state.filter.page = page;
            getLists(true);
        }

        function findKeyword() {
            var keyword = ($keywordInput.val() || '').trim();
            if (keyword === state.prevKeyword) {
                return;
            }
            state.prevKeyword = keyword;
            state.filter.keyword = keyword;
            clearTimeout(state.keywordTimer);
            state.keywordTimer = setTimeout(function () {
                getLists();
            }, 400);
        }

        function updateCollect(list, typ) {
            if (!options.collectAction) {
                return;
            }
            setLoading(true);
            $.ajax({
                url: options.collectAction,
                type: 'POST',
                data: { ID: list.ID, Typ: typ }
            }).done(function (response) {
                if (response.StatusCode === 200) {
                    list.Collect = list.Collect === 1 ? 0 : 1;
                    renderResults();
                } else if (response.StatusCode === 401) {
                    showMessage(response.Error_msg);
                }
                setLoading(false);
            }).fail(function (err) {
                console.log(err);
                setLoading(false);
            });
        }

        function getLists(isPageUpdate) {
            if (!isPageUpdate) {
                state.filter.page = 1;
            }
            setLoading(true);

            var payload = {
                Page: state.filter.page,
                Limit: state.filter.limit,
                Keyword: state.filter.keyword,
                Ord: state.filter.ord
            };
            categoryDefs.forEach(function (def, index) {
                var active = state.activeBtns[index];
                payload[def.paramKey] = (active && active.btn) ? active.btn.ID : '';
            });

            $.ajax({
                url: options.listsAction,
                type: 'POST',
                data: payload
            }).done(function (response) {
                if (response.StatusCode === 200) {
                    state.lists = response.Data || [];
                    state.lists.forEach(function (item) {
                        item.color = '';
                        item.SchemaBadgeColor = '#F6D700';
                        switch (item.QualityBadgeType) {
                            case 1:
                                item.color = '#B88230';
                                break;
                            case 2:
                                item.color = '#909399';
                                break;
                            case 3:
                                item.color = '#E6A23C';
                                break;
                        }
                    });
                    state.totalPage = response.Total_pages;
                    state.totalCount = response.Total_count;
                    state.page = response.Page;
                    render();
                }
                setLoading(false);
            }).fail(function (err) {
                console.log(err);
                setLoading(false);
            });
        }

        function getCategories() {
            if (!options.categoriesAction) {
                getLists();
                return;
            }
            $.ajax({
                url: options.categoriesAction,
                type: 'GET'
            }).done(function (response) {
                state.categories = [];
                state.activeBtns = [];
                categoryDefs.forEach(function (def) {
                    state.categories.push({ title: def.title, btns: response[def.dataKey] || [] });
                    state.activeBtns.push({ btn: null, index: null });
                });
                renderCategoryNav();
                getLists();
            }).fail(function (err) {
                console.log(err);
            });
        }

        // event wiring
        $keywordInput.on('keyup', findKeyword);
        $limitSelect.on('change', function () {
            state.filter.limit = parseInt($(this).val(), 10);
            getLists(true);
        });
        $gotoPageInput.on('change', function () {
            state.filter.page = parseInt($(this).val(), 10) || 1;
        });
        $root.find('[data-role="goto-page-btn"]').on('click', function () { getLists(true); });
        $prevBtn.on('click', function () { goPage(state.filter.page - 1); });
        $nextBtn.on('click', function () { goPage(state.filter.page + 1); });

        getCategories();

        return {
            state: state,
            getLists: getLists,
            updateCollect: updateCollect,
            render: render
        };
    }

    window.OpenData = { init: init };
})(jQuery, window);
