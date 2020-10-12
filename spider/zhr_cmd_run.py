import os
import time
while True:
    #
    try:
        os.system('python /work/zjr/spider/run.py --debug --config /work/zjr/zhihu/test/zjr_zhihu_list.py --log_level error')
        # os.system('python run.py --debug --config /work/zjr/spider/zjr_weibo_remen_details_test.py --log_level error')
        # time.sleep(60)
        # os.system('python run.py --debug --config /work/zjr/spider/zjr_qzwb_detail.py --log_level error')
        # os.system(
        #     'python /work/zjr/spider/run.py --debug --config /work/zjr/spider/zjr_weibo_user_content_details.py --log_level error')
    except:
        pass
    time.sleep(10)