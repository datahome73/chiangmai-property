import asyncio
import sys
sys.path.insert(0, '/home/datahome/chiangmai-property/backend')

async def main():
    # Test schema imports
    from app.schemas import (
        PriceTypeEnum, PropertyTypeEnum, PropertyResponse,
        PropertyListResponse, PropertyFilterParams, MarkerResponse,
        DistrictResponse, CompareRequest, CompareResponse,
        UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
        FavoriteCreate, FavoriteResponse, ComparisonCreate, ComparisonResponse,
    )
    print("✅ All schemas imported successfully")

    # Test service imports
    from app.services import (
        get_properties, get_property_detail, get_properties_for_compare,
        get_markers, get_districts,
        register_user, authenticate_user, create_token, get_current_user,
        get_user_favorites, add_favorite, remove_favorite,
        get_user_comparisons, save_comparison, delete_comparison,
    )
    print("✅ All services imported successfully")

    # Test that services are callable
    import inspect
    print(f"\n📋 Property service functions:")
    for name in ['get_properties', 'get_property_detail', 'get_properties_for_compare', 'get_markers', 'get_districts']:
        fn = globals()['get_properties' if name == 'get_properties' else name]
        # Just check they exist as async functions
        print(f"   {name}: {inspect.iscoroutinefunction(eval(name))}")

    print(f"\n📋 Auth service functions:")
    for name in ['register_user', 'authenticate_user', 'create_token', 'get_current_user']:
        fn = eval(name)
        print(f"   {name}: async={inspect.iscoroutinefunction(fn)}")

    print(f"\n📋 Favorite service functions:")
    for name in ['get_user_favorites', 'add_favorite', 'remove_favorite', 'get_user_comparisons', 'save_comparison', 'delete_comparison']:
        fn = eval(name)
        print(f"   {name}: async={inspect.iscoroutinefunction(fn)}")

    # Quick schema instantiation test
    prop_resp = PropertyResponse(
        id=1, title="Test Property", price_type=PriceTypeEnum.RENT,
        property_type=PropertyTypeEnum.CONDO, source="test"
    )
    print(f"\n✅ PropertyResponse created: id={prop_resp.id}, title='{prop_resp.title}'")

    filter_params = PropertyFilterParams(keyword="test", page=1, page_size=20)
    print(f"✅ PropertyFilterParams created: keyword={filter_params.keyword}")

    print("\n🎉 All checks passed!")

# Need to re-import globals properly
if __name__ == "__main__":
    asyncio.run(main())
