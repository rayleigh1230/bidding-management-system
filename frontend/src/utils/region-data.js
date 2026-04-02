// 中国行政区划数据 (省/市/区三级)
// 数据格式: [{ value, label, children: [{ value, label, children: [{ value, label }] }] }]
export const regionData = [
  {
    value: '北京市', label: '北京市', children: [
      { value: '北京市', label: '北京市', children: [
        { value: '东城区', label: '东城区' }, { value: '西城区', label: '西城区' },
        { value: '朝阳区', label: '朝阳区' }, { value: '丰台区', label: '丰台区' },
        { value: '石景山区', label: '石景山区' }, { value: '海淀区', label: '海淀区' },
        { value: '顺义区', label: '顺义区' }, { value: '通州区', label: '通州区' },
        { value: '大兴区', label: '大兴区' }, { value: '房山区', label: '房山区' },
        { value: '门头沟区', label: '门头沟区' }, { value: '昌平区', label: '昌平区' },
        { value: '平谷区', label: '平谷区' }, { value: '密云区', label: '密云区' },
        { value: '怀柔区', label: '怀柔区' }, { value: '延庆区', label: '延庆区' },
      ] },
    ],
  },
  {
    value: '上海市', label: '上海市', children: [
      { value: '上海市', label: '上海市', children: [
        { value: '黄浦区', label: '黄浦区' }, { value: '徐汇区', label: '徐汇区' },
        { value: '长宁区', label: '长宁区' }, { value: '静安区', label: '静安区' },
        { value: '普陀区', label: '普陀区' }, { value: '虹口区', label: '虹口区' },
        { value: '杨浦区', label: '杨浦区' }, { value: '浦东新区', label: '浦东新区' },
        { value: '闵行区', label: '闵行区' }, { value: '宝山区', label: '宝山区' },
        { value: '嘉定区', label: '嘉定区' }, { value: '金山区', label: '金山区' },
        { value: '松江区', label: '松江区' }, { value: '青浦区', label: '青浦区' },
        { value: '奉贤区', label: '奉贤区' }, { value: '崇明区', label: '崇明区' },
      ] },
    ],
  },
  {
    value: '天津市', label: '天津市', children: [
      { value: '天津市', label: '天津市', children: [
        { value: '和平区', label: '和平区' }, { value: '河东区', label: '河东区' },
        { value: '河西区', label: '河西区' }, { value: '南开区', label: '南开区' },
        { value: '河北区', label: '河北区' }, { value: '红桥区', label: '红桥区' },
        { value: '东丽区', label: '东丽区' }, { value: '西青区', label: '西青区' },
        { value: '津南区', label: '津南区' }, { value: '北辰区', label: '北辰区' },
        { value: '武清区', label: '武清区' }, { value: '宝坻区', label: '宝坻区' },
        { value: '滨海新区', label: '滨海新区' },
      ] },
    ],
  },
  {
    value: '重庆市', label: '重庆市', children: [
      { value: '重庆市', label: '重庆市', children: [
        { value: '渝中区', label: '渝中区' }, { value: '万州区', label: '万州区' },
        { value: '涪陵区', label: '涪陵区' }, { value: '大渡口区', label: '大渡口区' },
        { value: '江北区', label: '江北区' }, { value: '沙坪坝区', label: '沙坪坝区' },
        { value: '九龙坡区', label: '九龙坡区' }, { value: '南岸区', label: '南岸区' },
        { value: '北碚区', label: '北碚区' }, { value: '渝北区', label: '渝北区' },
        { value: '巴南区', label: '巴南区' }, { value: '合川区', label: '合川区' },
        { value: '永川区', label: '永川区' }, { value: '江津区', label: '江津区' },
      ] },
    ],
  },
  {
    value: '浙江省', label: '浙江省', children: [
      { value: '杭州市', label: '杭州市', children: [
        { value: '上城区', label: '上城区' }, { value: '拱墅区', label: '拱墅区' },
        { value: '西湖区', label: '西湖区' }, { value: '滨江区', label: '滨江区' },
        { value: '萧山区', label: '萧山区' }, { value: '余杭区', label: '余杭区' },
        { value: '临平区', label: '临平区' }, { value: '钱塘区', label: '钱塘区' },
        { value: '富阳区', label: '富阳区' }, { value: '临安区', label: '临安区' },
        { value: '桐庐县', label: '桐庐县' }, { value: '淳安县', label: '淳安县' },
        { value: '建德市', label: '建德市' },
      ] },
      { value: '宁波市', label: '宁波市', children: [
        { value: '海曙区', label: '海曙区' }, { value: '江北区', label: '江北区' },
        { value: '北仑区', label: '北仑区' }, { value: '镇海区', label: '镇海区' },
        { value: '鄞州区', label: '鄞州区' }, { value: '奉化区', label: '奉化区' },
        { value: '余姚市', label: '余姚市' }, { value: '慈溪市', label: '慈溪市' },
        { value: '宁海县', label: '宁海县' }, { value: '象山县', label: '象山县' },
      ] },
      { value: '温州市', label: '温州市', children: [
        { value: '鹿城区', label: '鹿城区' }, { value: '龙湾区', label: '龙湾区' },
        { value: '瓯海区', label: '瓯海区' }, { value: '洞头区', label: '洞头区' },
        { value: '瑞安市', label: '瑞安市' }, { value: '乐清市', label: '乐清市' },
      ] },
      { value: '嘉兴市', label: '嘉兴市', children: [
        { value: '南湖区', label: '南湖区' }, { value: '秀洲区', label: '秀洲区' },
        { value: '海宁市', label: '海宁市' }, { value: '平湖市', label: '平湖市' },
        { value: '桐乡市', label: '桐乡市' }, { value: '嘉善县', label: '嘉善县' }, { value: '海盐县', label: '海盐县' },
      ] },
      { value: '湖州市', label: '湖州市', children: [
        { value: '吴兴区', label: '吴兴区' }, { value: '南浔区', label: '南浔区' },
        { value: '德清县', label: '德清县' }, { value: '长兴县', label: '长兴县' }, { value: '安吉县', label: '安吉县' },
      ] },
      { value: '绍兴市', label: '绍兴市', children: [
        { value: '越城区', label: '越城区' }, { value: '柯桥区', label: '柯桥区' },
        { value: '上虞区', label: '上虞区' }, { value: '诸暨市', label: '诸暨市' }, { value: '嵊州市', label: '嵊州市' },
      ] },
      { value: '金华市', label: '金华市', children: [
        { value: '婺城区', label: '婺城区' }, { value: '金东区', label: '金东区' },
        { value: '义乌市', label: '义乌市' }, { value: '东阳市', label: '东阳市' }, { value: '永康市', label: '永康市' },
      ] },
      { value: '衢州市', label: '衢州市', children: [
        { value: '柯城区', label: '柯城区' }, { value: '衢江区', label: '衢江区' }, { value: '江山市', label: '江山市' },
      ] },
      { value: '舟山市', label: '舟山市', children: [
        { value: '定海区', label: '定海区' }, { value: '普陀区', label: '普陀区' },
      ] },
      { value: '台州市', label: '台州市', children: [
        { value: '椒江区', label: '椒江区' }, { value: '黄岩区', label: '黄岩区' }, { value: '路桥区', label: '路桥区' },
        { value: '温岭市', label: '温岭市' }, { value: '临海市', label: '临海市' },
      ] },
      { value: '丽水市', label: '丽水市', children: [
        { value: '莲都区', label: '莲都区' }, { value: '龙泉市', label: '龙泉市' },
      ] },
    ],
  },
  {
    value: '江苏省', label: '江苏省', children: [
      { value: '南京市', label: '南京市', children: [
        { value: '玄武区', label: '玄武区' }, { value: '秦淮区', label: '秦淮区' },
        { value: '建邺区', label: '建邺区' }, { value: '鼓楼区', label: '鼓楼区' },
        { value: '栖霞区', label: '栖霞区' }, { value: '雨花台区', label: '雨花台区' },
        { value: '江宁区', label: '江宁区' }, { value: '浦口区', label: '浦口区' },
        { value: '六合区', label: '六合区' }, { value: '溧水区', label: '溧水区' }, { value: '高淳区', label: '高淳区' },
      ] },
      { value: '苏州市', label: '苏州市', children: [
        { value: '姑苏区', label: '姑苏区' }, { value: '虎丘区', label: '虎丘区' },
        { value: '吴中区', label: '吴中区' }, { value: '相城区', label: '相城区' },
        { value: '吴江区', label: '吴江区' }, { value: '昆山市', label: '昆山市' },
        { value: '常熟市', label: '常熟市' }, { value: '张家港市', label: '张家港市' }, { value: '太仓市', label: '太仓市' },
      ] },
      { value: '无锡市', label: '无锡市', children: [
        { value: '锡山区', label: '锡山区' }, { value: '惠山区', label: '惠山区' },
        { value: '滨湖区', label: '滨湖区' }, { value: '梁溪区', label: '梁溪区' },
        { value: '新吴区', label: '新吴区' }, { value: '江阴市', label: '江阴市' }, { value: '宜兴市', label: '宜兴市' },
      ] },
      { value: '常州市', label: '常州市', children: [
        { value: '天宁区', label: '天宁区' }, { value: '钟楼区', label: '钟楼区' },
        { value: '新北区', label: '新北区' }, { value: '武进区', label: '武进区' }, { value: '金坛区', label: '金坛区' },
      ] },
      { value: '南通市', label: '南通市', children: [
        { value: '崇川区', label: '崇川区' }, { value: '通州区', label: '通州区' },
        { value: '海门区', label: '海门区' }, { value: '如东县', label: '如东县' }, { value: '启东市', label: '启东市' },
      ] },
      { value: '扬州市', label: '扬州市', children: [
        { value: '广陵区', label: '广陵区' }, { value: '邗江区', label: '邗江区' }, { value: '江都区', label: '江都区' },
      ] },
      { value: '徐州市', label: '徐州市', children: [
        { value: '鼓楼区', label: '鼓楼区' }, { value: '云龙区', label: '云龙区' }, { value: '贾汪区', label: '贾汪区' }, { value: '泉山区', label: '泉山区' },
      ] },
    ],
  },
  {
    value: '广东省', label: '广东省', children: [
      { value: '广州市', label: '广州市', children: [
        { value: '越秀区', label: '越秀区' }, { value: '海珠区', label: '海珠区' },
        { value: '荔湾区', label: '荔湾区' }, { value: '天河区', label: '天河区' },
        { value: '白云区', label: '白云区' }, { value: '番禺区', label: '番禺区' },
        { value: '花都区', label: '花都区' }, { value: '南沙区', label: '南沙区' },
        { value: '从化区', label: '从化区' }, { value: '增城区', label: '增城区' },
      ] },
      { value: '深圳市', label: '深圳市', children: [
        { value: '罗湖区', label: '罗湖区' }, { value: '福田区', label: '福田区' },
        { value: '南山区', label: '南山区' }, { value: '宝安区', label: '宝安区' },
        { value: '龙岗区', label: '龙岗区' }, { value: '盐田区', label: '盐田区' },
        { value: '龙华区', label: '龙华区' }, { value: '坪山区', label: '坪山区' },
        { value: '光明区', label: '光明区' },
      ] },
      { value: '珠海市', label: '珠海市', children: [
        { value: '香洲区', label: '香洲区' }, { value: '斗门区', label: '斗门区' }, { value: '金湾区', label: '金湾区' },
      ] },
      { value: '东莞市', label: '东莞市', children: [
        { value: '莞城街道', label: '莞城街道' }, { value: '南城街道', label: '南城街道' }, { value: '东城街道', label: '东城街道' },
      ] },
      { value: '佛山市', label: '佛山市', children: [
        { value: '禅城区', label: '禅城区' }, { value: '南海区', label: '南海区' }, { value: '顺德区', label: '顺德区' },
      ] },
    ],
  },
  {
    value: '四川省', label: '四川省', children: [
      { value: '成都市', label: '成都市', children: [
        { value: '锦江区', label: '锦江区' }, { value: '青羊区', label: '青羊区' },
        { value: '金牛区', label: '金牛区' }, { value: '武侯区', label: '武侯区' },
        { value: '成华区', label: '成华区' }, { value: '龙泉驿区', label: '龙泉驿区' },
        { value: '青白江区', label: '青白江区' }, { value: '新都区', label: '新都区' },
        { value: '温江区', label: '温江区' }, { value: '双流区', label: '双流区' },
        { value: '郫都区', label: '郫都区' },
      ] },
    ],
  },
  {
    value: '湖北省', label: '湖北省', children: [
      { value: '武汉市', label: '武汉市', children: [
        { value: '江岸区', label: '江岸区' }, { value: '江汉区', label: '江汉区' },
        { value: '硚口区', label: '硚口区' }, { value: '汉阳区', label: '汉阳区' },
        { value: '武昌区', label: '武昌区' }, { value: '青山区', label: '青山区' },
        { value: '洪山区', label: '洪山区' }, { value: '东西湖区', label: '东西湖区' },
      ] },
    ],
  },
  {
    value: '湖南省', label: '湖南省', children: [
      { value: '长沙市', label: '长沙市', children: [
        { value: '芙蓉区', label: '芙蓉区' }, { value: '天心区', label: '天心区' },
        { value: '岳麓区', label: '岳麓区' }, { value: '开福区', label: '开福区' },
        { value: '雨花区', label: '雨花区' }, { value: '望城区', label: '望城区' }, { value: '长沙县', label: '长沙县' },
      ] },
    ],
  },
  {
    value: '山东省', label: '山东省', children: [
      { value: '济南市', label: '济南市', children: [
        { value: '历下区', label: '历下区' }, { value: '市中区', label: '市中区' },
        { value: '槐荫区', label: '槐荫区' }, { value: '天桥区', label: '天桥区' },
        { value: '历城区', label: '历城区' }, { value: '长清区', label: '长清区' },
      ] },
      { value: '青岛市', label: '青岛市', children: [
        { value: '市南区', label: '市南区' }, { value: '市北区', label: '市北区' },
        { value: '黄岛区', label: '黄岛区' }, { value: '崂山区', label: '崂山区' },
        { value: '李沧区', label: '李沧区' }, { value: '城阳区', label: '城阳区' },
      ] },
    ],
  },
  {
    value: '河南省', label: '河南省', children: [
      { value: '郑州市', label: '郑州市', children: [
        { value: '中原区', label: '中原区' }, { value: '二七区', label: '二七区' },
        { value: '管城区', label: '管城区' }, { value: '金水区', label: '金水区' },
        { value: '上街区', label: '上街区' }, { value: '惠济区', label: '惠济区' },
      ] },
    ],
  },
  {
    value: '河北省', label: '河北省', children: [
      { value: '石家庄市', label: '石家庄市', children: [
        { value: '长安区', label: '长安区' }, { value: '桥西区', label: '桥西区' },
        { value: '新华区', label: '新华区' }, { value: '裕华区', label: '裕华区' },
      ] },
    ],
  },
  {
    value: '福建省', label: '福建省', children: [
      { value: '福州市', label: '福州市', children: [
        { value: '鼓楼区', label: '鼓楼区' }, { value: '台江区', label: '台江区' },
        { value: '仓山区', label: '仓山区' }, { value: '马尾区', label: '马尾区' }, { value: '晋安区', label: '晋安区' },
      ] },
      { value: '厦门市', label: '厦门市', children: [
        { value: '思明区', label: '思明区' }, { value: '海沧区', label: '海沧区' },
        { value: '湖里区', label: '湖里区' }, { value: '集美区', label: '集美区' },
        { value: '同安区', label: '同安区' }, { value: '翔安区', label: '翔安区' },
      ] },
    ],
  },
  {
    value: '安徽省', label: '安徽省', children: [
      { value: '合肥市', label: '合肥市', children: [
        { value: '瑶海区', label: '瑶海区' }, { value: '庐阳区', label: '庐阳区' },
        { value: '蜀山区', label: '蜀山区' }, { value: '包河区', label: '包河区' },
      ] },
    ],
  },
  {
    value: '江西省', label: '江西省', children: [
      { value: '南昌市', label: '南昌市', children: [
        { value: '东湖区', label: '东湖区' }, { value: '西湖区', label: '西湖区' },
        { value: '青云谱区', label: '青云谱区' }, { value: '青山湖区', label: '青山湖区' }, { value: '新建区', label: '新建区' },
      ] },
    ],
  },
  {
    value: '辽宁省', label: '辽宁省', children: [
      { value: '沈阳市', label: '沈阳市', children: [
        { value: '和平区', label: '和平区' }, { value: '沈河区', label: '沈河区' },
        { value: '大东区', label: '大东区' }, { value: '皇姑区', label: '皇姑区' }, { value: '铁西区', label: '铁西区' },
      ] },
      { value: '大连市', label: '大连市', children: [
        { value: '中山区', label: '中山区' }, { value: '西岗区', label: '西岗区' },
        { value: '沙河口区', label: '沙河口区' }, { value: '甘井子区', label: '甘井子区' },
      ] },
    ],
  },
  {
    value: '吉林省', label: '吉林省', children: [
      { value: '长春市', label: '长春市', children: [
        { value: '南关区', label: '南关区' }, { value: '宽城区', label: '宽城区' },
        { value: '朝阳区', label: '朝阳区' }, { value: '二道区', label: '二道区' }, { value: '绿园区', label: '绿园区' },
      ] },
    ],
  },
  {
    value: '黑龙江省', label: '黑龙江省', children: [
      { value: '哈尔滨市', label: '哈尔滨市', children: [
        { value: '道里区', label: '道里区' }, { value: '南岗区', label: '南岗区' },
        { value: '道外区', label: '道外区' }, { value: '平房区', label: '平房区' }, { value: '松北区', label: '松北区' },
      ] },
    ],
  },
  {
    value: '陕西省', label: '陕西省', children: [
      { value: '西安市', label: '西安市', children: [
        { value: '新城区', label: '新城区' }, { value: '碑林区', label: '碑林区' },
        { value: '莲湖区', label: '莲湖区' }, { value: '雁塔区', label: '雁塔区' },
        { value: '灞桥区', label: '灞桥区' }, { value: '未央区', label: '未央区' },
      ] },
    ],
  },
  {
    value: '山西省', label: '山西省', children: [
      { value: '太原市', label: '太原市', children: [
        { value: '小店区', label: '小店区' }, { value: '迎泽区', label: '迎泽区' },
        { value: '杏花岭区', label: '杏花岭区' }, { value: '尖草坪区', label: '尖草坪区' }, { value: '万柏林区', label: '万柏林区' },
      ] },
    ],
  },
  {
    value: '甘肃省', label: '甘肃省', children: [
      { value: '兰州市', label: '兰州市', children: [
        { value: '城关区', label: '城关区' }, { value: '七里河区', label: '七里河区' },
        { value: '西固区', label: '西固区' }, { value: '安宁区', label: '安宁区' },
      ] },
    ],
  },
  {
    value: '青海省', label: '青海省', children: [
      { value: '西宁市', label: '西宁市', children: [
        { value: '城东区', label: '城东区' }, { value: '城中区', label: '城中区' },
        { value: '城西区', label: '城西区' }, { value: '城北区', label: '城北区' },
      ] },
    ],
  },
  {
    value: '云南省', label: '云南省', children: [
      { value: '昆明市', label: '昆明市', children: [
        { value: '五华区', label: '五华区' }, { value: '盘龙区', label: '盘龙区' },
        { value: '官渡区', label: '官渡区' }, { value: '西山区', label: '西山区' }, { value: '呈贡区', label: '呈贡区' },
      ] },
    ],
  },
  {
    value: '贵州省', label: '贵州省', children: [
      { value: '贵阳市', label: '贵阳市', children: [
        { value: '南明区', label: '南明区' }, { value: '云岩区', label: '云岩区' },
        { value: '花溪区', label: '花溪区' }, { value: '乌当区', label: '乌当区' }, { value: '白云区', label: '白云区' },
      ] },
    ],
  },
  {
    value: '海南省', label: '海南省', children: [
      { value: '海口市', label: '海口市', children: [
        { value: '秀英区', label: '秀英区' }, { value: '龙华区', label: '龙华区' },
        { value: '琼山区', label: '琼山区' }, { value: '美兰区', label: '美兰区' },
      ] },
    ],
  },
  {
    value: '广西壮族自治区', label: '广西壮族自治区', children: [
      { value: '南宁市', label: '南宁市', children: [
        { value: '兴宁区', label: '兴宁区' }, { value: '青秀区', label: '青秀区' },
        { value: '江南区', label: '江南区' }, { value: '西乡塘区', label: '西乡塘区' },
      ] },
    ],
  },
  {
    value: '内蒙古自治区', label: '内蒙古自治区', children: [
      { value: '呼和浩特市', label: '呼和浩特市', children: [
        { value: '新城区', label: '新城区' }, { value: '回民区', label: '回民区' },
        { value: '玉泉区', label: '玉泉区' }, { value: '赛罕区', label: '赛罕区' },
      ] },
    ],
  },
  {
    value: '西藏自治区', label: '西藏自治区', children: [
      { value: '拉萨市', label: '拉萨市', children: [
        { value: '城关区', label: '城关区' }, { value: '堆龙德庆区', label: '堆龙德庆区' },
      ] },
    ],
  },
  {
    value: '宁夏回族自治区', label: '宁夏回族自治区', children: [
      { value: '银川市', label: '银川市', children: [
        { value: '兴庆区', label: '兴庆区' }, { value: '西夏区', label: '西夏区' }, { value: '金凤区', label: '金凤区' },
      ] },
    ],
  },
  {
    value: '新疆维吾尔自治区', label: '新疆维吾尔自治区', children: [
      { value: '乌鲁木齐市', label: '乌鲁木齐市', children: [
        { value: '天山区', label: '天山区' }, { value: '沙依巴克区', label: '沙依巴克区' },
        { value: '新市区', label: '新市区' }, { value: '水磨沟区', label: '水磨沟区' },
      ] },
    ],
  },
  {
    value: '香港特别行政区', label: '香港特别行政区', children: [
      { value: '香港岛', label: '香港岛', children: [{ value: '中西区', label: '中西区' }, { value: '湾仔区', label: '湾仔区' }] },
    ],
  },
  {
    value: '澳门特别行政区', label: '澳门特别行政区', children: [
      { value: '澳门半岛', label: '澳门半岛', children: [{ value: '花地玛堂区', label: '花地玛堂区' }] },
    ],
  },
  {
    value: '台湾省', label: '台湾省', children: [
      { value: '台北市', label: '台北市', children: [{ value: '中正区', label: '中正区' }, { value: '大同区', label: '大同区' }] },
    ],
  },
]
