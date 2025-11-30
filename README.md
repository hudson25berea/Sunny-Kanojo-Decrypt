# Sunny-Kanojo-Decrypt
解包 超次元彼女

解密部分感谢[劃破黑夜](https://github.com/28598519a) 的[Kanojo_AssetDecDL](https://github.com/28598519a/Kanojo_AssetDecDL)提供的方法以及文件名映射思路

# 使用说明

需要xxtea和tqdm库

## 1.获取文件

注意，使用下面方法获取游戏文件仍然可能获取不全

需要访问安卓的/data/data/jp.sunny.kanojo/files获取一部分文件，同时利用该repo中的download_hotres.py才能获取尽可能多的文件

## 2.解密几个重要文件

需要利用auxiliary_decrypt.py解密下面几个文件：

bundleRes/bundle_file_list.dat

bundleRes/login_protector.dat

bundleRes/protector.dat

hotRes/login_protector.dat

hotRes/protector.dat

## 3.解密并利用上面几个文件还原文件名

运行restore_kanojo_final_v6.py并填入对应信息即可

## 4.（可选）利用几个organize自动构建可以在live2dviewerEX中直接使用的spine2d配置

使用几个organize_xxx.py生成配置的json文件

这步还原的配置可能不准确，根据需要自行更改

# 免责声明 (Disclaimer)

如果您是相关内容的版权拥有者，且认为本项目侵犯了您的权益，请提交 Issue 删除。
